from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from alloy_api.auth.cookies import clear_session_cookie, set_session_cookie
from alloy_api.auth.deps import CurrentPrincipal, CurrentUserDep, unauthorized
from alloy_api.auth.emails import (
    account_deletion_email,
    email_change_email,
    email_changed_notice,
    password_reset_email,
    verification_email,
)
from alloy_api.auth.models import User, UserSession
from alloy_api.auth.passwords import hash_password, verify_password
from alloy_api.auth.schemas import (
    AccountDeletion,
    Credentials,
    EmailChangeConfirmation,
    EmailChangeRequest,
    EmailVerification,
    PasswordChange,
    PasswordReset,
    PasswordResetRequest,
    UserRead,
)
from alloy_api.auth.tokens import hash_token, new_token
from alloy_api.config import SettingsDep
from alloy_api.db import SessionDep
from alloy_api.jobs.emails import send_email
from alloy_api.models import utcnow
from alloy_api.ratelimit import (
    CHANGE_EMAIL_PER_USER,
    FORGOT_PASSWORD_PER_EMAIL,
    FORGOT_PASSWORD_PER_IP,
    LOGIN_PER_EMAIL,
    LOGIN_PER_IP,
    RESEND_VERIFICATION_PER_USER,
    SIGNUP_PER_IP,
    TOKEN_PER_IP,
    LimiterDep,
    per_ip,
)
from alloy_api.workspaces.models import (
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
    WorkspaceRole,
)
from alloy_api.workspaces.service import DEFAULT_WORKSPACE_NAME, create_workspace

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


async def start_session(
    session: AsyncSession, settings: Settings, user: User, response: Response
) -> UserRead:
    """Create a session row and put its token in the cookie. Logging in is how a
    deletion is undone, so a pending one is cleared here."""
    token = new_token()
    now = utcnow()
    user.deleted_at = None
    session.add(
        UserSession(
            user=user,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + settings.session_ttl,
        )
    )
    await session.commit()
    set_session_cookie(response, token, settings.session_ttl)
    return UserRead.model_validate(user)


async def send_verification(session: AsyncSession, settings: Settings, user: User) -> None:
    """Issue a fresh verification token, replacing any pending one, and queue the email."""
    token = new_token()
    user.verification_token_hash = hash_token(token)
    user.verification_sent_at = utcnow()
    await session.commit()
    await send_email.kiq(verification_email(user, token, str(settings.frontend_url)))


async def send_password_reset(session: AsyncSession, settings: Settings, user: User) -> None:
    """Issue a fresh reset token, replacing any pending one, and queue the email."""
    token = new_token()
    user.password_reset_token_hash = hash_token(token)
    user.password_reset_sent_at = utcnow()
    await session.commit()
    await send_email.kiq(
        password_reset_email(user, token, str(settings.frontend_url), settings.password_reset_ttl)
    )


def clear_password_reset(user: User) -> None:
    user.password_reset_token_hash = None
    user.password_reset_sent_at = None


def clear_email_change(user: User) -> None:
    user.pending_email = None
    user.email_change_token_hash = None
    user.email_change_sent_at = None


async def email_taken(session: AsyncSession, email: str) -> bool:
    return await session.scalar(select(User.id).where(User.email == email).limit(1)) is not None


async def workspaces_needing_an_owner(session: AsyncSession, user: User) -> list[str]:
    """Names of the workspaces `user` is the only owner of that have other members:
    deleting the account would leave nobody able to manage them."""
    other = aliased(WorkspaceMember)
    others = (
        select(func.count(other.id))
        .where(other.workspace_id == Workspace.id)
        .where(other.user_id != user.id)
        .correlate(Workspace)
        .scalar_subquery()
    )
    other_owners = (
        select(func.count(other.id))
        .join(User, User.id == other.user_id)
        .where(other.workspace_id == Workspace.id)
        .where(other.user_id != user.id)
        .where(other.role == WorkspaceRole.OWNER)
        .where(User.deleted_at.is_(None))
        .correlate(Workspace)
        .scalar_subquery()
    )
    names = await session.scalars(
        select(Workspace.name)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .where(WorkspaceMember.role == WorkspaceRole.OWNER)
        .where(others > 0)
        .where(other_owners == 0)
        .order_by(Workspace.name)
    )
    return list(names)


async def has_pending_invite(session: AsyncSession, email: str) -> bool:
    """Whether an invitation is waiting for this address. Accepting it verifies the
    email, so such a signup gets no verification email of its own."""
    invite_id = await session.scalar(
        select(WorkspaceInvite.id)
        .where(WorkspaceInvite.email == email)
        .where(WorkspaceInvite.accepted_at.is_(None))
        .where(WorkspaceInvite.revoked_at.is_(None))
        .where(WorkspaceInvite.expires_at > utcnow())
        .limit(1)
    )
    return invite_id is not None


async def revoke_sessions(session: AsyncSession, user_id: UUID, *, keep: UUID | None) -> None:
    statement = (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    if keep is not None:
        statement = statement.where(UserSession.id != keep)
    await session.execute(statement)
    await session.commit()


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(per_ip(SIGNUP_PER_IP))],
)
async def signup(
    credentials: Credentials,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
) -> UserRead:
    """Create an account, a first workspace owned by it, log in, and email a
    verification link. Until it is followed, the account can only use `/auth/*`.

    An invitee gets no link: accepting the invitation verifies the address instead.
    """
    user = User(
        email=credentials.email.lower(), password_hash=await hash_password(credentials.password)
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    create_workspace(session, DEFAULT_WORKSPACE_NAME, user)
    read = await start_session(session, settings, user, response)
    if not await has_pending_invite(session, user.email):
        await send_verification(session, settings, user)
    return read


@router.post("/verify-email", dependencies=[Depends(per_ip(TOKEN_PER_IP))])
async def verify_email(
    body: EmailVerification, session: SessionDep, settings: SettingsDep
) -> UserRead:
    """Follow the emailed link. No login needed: the link may be opened anywhere.

    404 for an unknown or already used token; 410 for an expired one.
    """
    user = await session.scalar(
        select(User).where(User.verification_token_hash == hash_token(body.token))
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verification link not found")
    sent_at = user.verification_sent_at
    if sent_at is None or sent_at + settings.verification_ttl <= utcnow():
        raise HTTPException(status.HTTP_410_GONE, "Verification link has expired")
    user.email_verified_at = utcnow()
    user.verification_token_hash = None
    user.verification_sent_at = None
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    user: CurrentUserDep, session: SessionDep, settings: SettingsDep, limiter: LimiterDep
) -> Response:
    """Email a new verification link; the previous one stops working."""
    if user.email_verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already verified")
    await limiter.hit(RESEND_VERIFICATION_PER_USER, str(user.id))
    await send_verification(session, settings, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login", dependencies=[Depends(per_ip(LOGIN_PER_IP))])
async def login(
    credentials: Credentials,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
    response: Response,
) -> UserRead:
    """The email counter counts failures only, and a success clears it. Both limits
    run before the password hash, which is slow by design."""
    email = credentials.email.lower()
    await limiter.check(LOGIN_PER_EMAIL, email)
    user = await session.scalar(select(User).where(User.email == email))
    if not await verify_password(credentials.password, user.password_hash if user else None):
        await limiter.hit(LOGIN_PER_EMAIL, email)
        raise unauthorized()
    assert user is not None  # noqa: S101 - verify_password fails on the dummy hash
    await limiter.reset(LOGIN_PER_EMAIL, email)
    return await start_session(session, settings, user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(principal: CurrentPrincipal, session: SessionDep) -> Response:
    """Revoke this session."""
    principal.session.revoked_at = utcnow()
    await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(principal: CurrentPrincipal, session: SessionDep) -> Response:
    """Revoke every session of the user: log out everywhere."""
    await revoke_sessions(session, principal.user.id, keep=None)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChange, principal: CurrentPrincipal, session: SessionDep
) -> Response:
    """Set a new password. Every other session is revoked; this one stays logged in."""
    if not await verify_password(body.current_password, principal.user.password_hash):
        raise unauthorized()
    principal.user.password_hash = await hash_password(body.new_password)
    # A reset link that was asked for earlier must not undo this change.
    clear_password_reset(principal.user)
    await revoke_sessions(session, principal.user.id, keep=principal.session.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(per_ip(FORGOT_PASSWORD_PER_IP))],
)
async def forgot_password(
    body: PasswordResetRequest, session: SessionDep, settings: SettingsDep, limiter: LimiterDep
) -> Response:
    """Email a password reset link to the address, if an account has it.

    Always 204, so the response does not reveal whether an account exists. A new
    request replaces the previous link. The email limit counts unknown addresses
    too, for the same reason.
    """
    email = body.email.lower()
    await limiter.hit(FORGOT_PASSWORD_PER_EMAIL, email)
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        await send_password_reset(session, settings, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", dependencies=[Depends(per_ip(TOKEN_PER_IP))])
async def reset_password(
    body: PasswordReset, session: SessionDep, settings: SettingsDep, response: Response
) -> UserRead:
    """Follow the emailed link: set the password and log in here.

    Every existing session is revoked, since whoever asked may have lost control of
    one. Following the link proves the address is the user's, so it also counts as
    email verification. 404 for an unknown or already used token; 410 for an expired
    one.
    """
    user = await session.scalar(
        select(User).where(User.password_reset_token_hash == hash_token(body.token))
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reset link not found")
    sent_at = user.password_reset_sent_at
    if sent_at is None or sent_at + settings.password_reset_ttl <= utcnow():
        raise HTTPException(status.HTTP_410_GONE, "Reset link has expired")
    user.password_hash = await hash_password(body.new_password)
    clear_password_reset(user)
    if not user.email_verified:
        user.email_verified_at = utcnow()
        user.verification_token_hash = None
        user.verification_sent_at = None
    await revoke_sessions(session, user.id, keep=None)
    return await start_session(session, settings, user, response)


@router.post("/change-email", status_code=status.HTTP_204_NO_CONTENT)
async def change_email(
    body: EmailChangeRequest,
    principal: CurrentPrincipal,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> Response:
    """Email a confirmation link to the new address; the account moves once it is
    followed. A new request replaces the pending one.

    Allowed before the current address is verified: a typo at signup is the
    usual reason to need this. 409 if the address is taken or unchanged.
    """
    user = principal.user
    new_email = body.new_email.lower()
    await limiter.check(CHANGE_EMAIL_PER_USER, str(user.id))
    if not await verify_password(body.current_password, user.password_hash):
        raise unauthorized()
    if new_email == user.email:
        raise HTTPException(status.HTTP_409_CONFLICT, "That is already your email")
    if await email_taken(session, new_email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    await limiter.hit(CHANGE_EMAIL_PER_USER, str(user.id))
    token = new_token()
    user.pending_email = new_email
    user.email_change_token_hash = hash_token(token)
    user.email_change_sent_at = utcnow()
    await session.commit()
    await send_email.kiq(
        email_change_email(new_email, token, str(settings.frontend_url), settings.email_change_ttl)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/change-email", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_email_change(principal: CurrentPrincipal, session: SessionDep) -> Response:
    """Drop the pending change; its link stops working. 204 when there is none too."""
    clear_email_change(principal.user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/confirm-email", dependencies=[Depends(per_ip(TOKEN_PER_IP))])
async def confirm_email(
    body: EmailChangeConfirmation, session: SessionDep, settings: SettingsDep
) -> UserRead:
    """Follow the link sent to the new address. No login needed: it may be opened
    anywhere. Reaching the new inbox proves it, so the account counts as
    verified. 404 for an unknown or used token; 410 for an expired one; 409 if
    the address was registered meanwhile.
    """
    user = await session.scalar(
        select(User).where(User.email_change_token_hash == hash_token(body.token))
    )
    if user is None or user.pending_email is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Confirmation link not found")
    sent_at = user.email_change_sent_at
    if sent_at is None or sent_at + settings.email_change_ttl <= utcnow():
        raise HTTPException(status.HTTP_410_GONE, "Confirmation link has expired")
    old_email, new_email = user.email, user.pending_email
    if await email_taken(session, new_email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user.email = new_email
    user.email_verified_at = utcnow()
    user.verification_token_hash = None
    user.verification_sent_at = None
    clear_email_change(user)
    await session.commit()
    await send_email.kiq(email_changed_notice(old_email, new_email))
    return UserRead.model_validate(user)


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: AccountDeletion, principal: CurrentPrincipal, session: SessionDep, settings: SettingsDep
) -> Response:
    """Schedule the account for deletion and log out everywhere.

    Logging in within `account_deletion_grace` brings the account back; after
    that the purge job removes it, with every workspace the user was alone in.
    409 while the user is the only owner of a shared workspace, which would
    otherwise be left with nobody to manage it.
    """
    user = principal.user
    if not await verify_password(body.current_password, user.password_hash):
        raise unauthorized()
    stranded = await workspaces_needing_an_owner(session, user)
    if stranded:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You are the only owner of: " + ", ".join(stranded) + ". Make someone else an "
            "owner, or delete the workspace, before deleting your account.",
        )
    user.deleted_at = utcnow()
    clear_email_change(user)
    clear_password_reset(user)
    await revoke_sessions(session, user.id, keep=None)
    await send_email.kiq(
        account_deletion_email(user, str(settings.frontend_url), settings.account_deletion_grace)
    )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.get("/me")
async def read_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)
