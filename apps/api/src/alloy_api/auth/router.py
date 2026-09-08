from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from alloy_api.auth.cookies import clear_session_cookie, set_session_cookie
from alloy_api.auth.deps import CurrentPrincipal, CurrentUserDep, unauthorized
from alloy_api.auth.emails import password_reset_email, verification_email
from alloy_api.auth.models import User, UserSession
from alloy_api.auth.passwords import hash_password, verify_password
from alloy_api.auth.schemas import (
    Credentials,
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
from alloy_api.workspaces.models import WorkspaceInvite
from alloy_api.workspaces.service import DEFAULT_WORKSPACE_NAME, create_workspace

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


async def start_session(
    session: AsyncSession, settings: Settings, user: User, response: Response
) -> UserRead:
    """Create a session row and put its token in the cookie."""
    token = new_token()
    now = utcnow()
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


@router.post("/signup", status_code=status.HTTP_201_CREATED)
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


@router.post("/verify-email")
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
    user: CurrentUserDep, session: SessionDep, settings: SettingsDep
) -> Response:
    """Email a new verification link; the previous one stops working."""
    if user.email_verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already verified")
    await send_verification(session, settings, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login")
async def login(
    credentials: Credentials, session: SessionDep, settings: SettingsDep, response: Response
) -> UserRead:
    user = await session.scalar(select(User).where(User.email == credentials.email.lower()))
    if not await verify_password(credentials.password, user.password_hash if user else None):
        raise unauthorized()
    assert user is not None  # noqa: S101 - verify_password fails on the dummy hash
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


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    body: PasswordResetRequest, session: SessionDep, settings: SettingsDep
) -> Response:
    """Email a password reset link to the address, if an account has it.

    Always 204, so the response does not reveal whether an account exists. A new
    request replaces the previous link.
    """
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if user is not None:
        await send_password_reset(session, settings, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password")
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


@router.get("/me")
async def read_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)
