from datetime import timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Response, status

from alloy_api.auth import service
from alloy_api.auth.cookies import clear_session_cookie, set_session_cookie
from alloy_api.auth.deps import CurrentPrincipal, CurrentUserDep, unauthorized
from alloy_api.auth.passwords import verify_password
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
from alloy_api.config import SettingsDep
from alloy_api.core.exceptions import ConflictError
from alloy_api.db.base import utcnow
from alloy_api.db.session import SessionDep
from alloy_api.integrations.ratelimit import TOKEN_PER_IP, Limit, LimiterDep, per_ip

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.auth.models import User
    from alloy_api.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_PER_IP = Limit("login:ip", 20, timedelta(minutes=15))
LOGIN_PER_EMAIL = Limit("login:email", 10, timedelta(minutes=15))
SIGNUP_PER_IP = Limit("signup:ip", 10, timedelta(hours=1))
FORGOT_PASSWORD_PER_IP = Limit("forgot-password:ip", 10, timedelta(hours=1))
FORGOT_PASSWORD_PER_EMAIL = Limit("forgot-password:email", 3, timedelta(hours=1))
RESEND_VERIFICATION_PER_USER = Limit("resend-verification:user", 3, timedelta(hours=1))
CHANGE_EMAIL_PER_USER = Limit("change-email:user", 3, timedelta(hours=1))


async def log_in(
    session: AsyncSession, settings: Settings, user: User, response: Response
) -> UserRead:
    token = await service.start_session(session, settings, user)
    set_session_cookie(response, token, settings.session_ttl)
    return UserRead.model_validate(user)


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
    user = await service.create_account(session, credentials.email.lower(), credentials.password)
    read = await log_in(session, settings, user, response)
    if not await service.has_pending_invite(session, user.email):
        await service.send_verification(session, settings, user)
    return read


@router.post("/verify-email", dependencies=[Depends(per_ip(TOKEN_PER_IP))])
async def verify_email(
    body: EmailVerification, session: SessionDep, settings: SettingsDep
) -> UserRead:
    """Follow the emailed link. No login needed: the link may be opened anywhere.

    404 for an unknown or already used token; 410 for an expired one.
    """
    return UserRead.model_validate(await service.verify_email(session, settings, body.token))


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    user: CurrentUserDep, session: SessionDep, settings: SettingsDep, limiter: LimiterDep
) -> Response:
    """Email a new verification link; the previous one stops working."""
    if user.email_verified:
        raise ConflictError("Email already verified")
    await limiter.hit(RESEND_VERIFICATION_PER_USER, str(user.id))
    await service.send_verification(session, settings, user)
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
    user = await service.user_by_email(session, email)
    if not await verify_password(credentials.password, user.password_hash if user else None):
        await limiter.hit(LOGIN_PER_EMAIL, email)
        raise unauthorized()
    assert user is not None  # noqa: S101 - verify_password fails on the dummy hash
    await limiter.reset(LOGIN_PER_EMAIL, email)
    return await log_in(session, settings, user, response)


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
    await service.revoke_sessions(session, principal.user.id, keep=None)
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
    await service.change_password(
        session, principal.user, body.new_password, keep=principal.session.id
    )
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
    user = await service.user_by_email(session, email)
    if user is not None:
        await service.send_password_reset(session, settings, user)
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
    user = await service.reset_password(session, settings, body.token, body.new_password)
    return await log_in(session, settings, user, response)


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
    if not await verify_password(body.current_password, user.password_hash):
        raise unauthorized()
    # Counted before the 409s, so a taken address costs an attempt too: otherwise
    # this would test addresses without limit.
    await limiter.hit(CHANGE_EMAIL_PER_USER, str(user.id))
    await service.request_email_change(session, settings, user, body.new_email.lower())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/change-email", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_email_change(principal: CurrentPrincipal, session: SessionDep) -> Response:
    """Drop the pending change; its link stops working. 204 when there is none too."""
    service.clear_email_change(principal.user)
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
    user = await service.confirm_email_change(session, settings, body.token)
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
    if not await verify_password(body.current_password, principal.user.password_hash):
        raise unauthorized()
    await service.schedule_deletion(session, settings, principal.user)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.get("/me")
async def read_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)
