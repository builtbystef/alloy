from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from alloy_api.auth.cookies import clear_session_cookie, set_session_cookie
from alloy_api.auth.deps import CurrentPrincipal, CurrentUserDep, unauthorized
from alloy_api.auth.models import User, UserSession
from alloy_api.auth.passwords import hash_password, verify_password
from alloy_api.auth.schemas import Credentials, PasswordChange, UserRead
from alloy_api.auth.tokens import hash_token, new_token
from alloy_api.config import SettingsDep
from alloy_api.db import SessionDep
from alloy_api.models import utcnow
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
    credentials: Credentials, session: SessionDep, settings: SettingsDep, response: Response
) -> UserRead:
    """Create an account, a first workspace owned by it, and log in."""
    user = User(
        email=credentials.email.lower(), password_hash=await hash_password(credentials.password)
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    create_workspace(session, DEFAULT_WORKSPACE_NAME, user)
    return await start_session(session, settings, user, response)


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
    await revoke_sessions(session, principal.user.id, keep=principal.session.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
async def read_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)
