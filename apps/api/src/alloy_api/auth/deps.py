from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.auth.cookies import SESSION_COOKIE
from alloy_api.auth.models import User, UserSession
from alloy_api.auth.tokens import hash_token
from alloy_api.db import SessionDep
from alloy_api.models import utcnow

# auto_error=False: a missing cookie is a 401 like an invalid one, not a 403.
session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    auto_error=False,
    description="Set by POST /auth/signup and /auth/login. HttpOnly: browsers send it themselves.",
)
SessionCookieDep = Annotated[str | None, Depends(session_cookie)]

# `last_used_at` is written at most this often per session, not on every request.
LAST_USED_RESOLUTION = timedelta(minutes=5)


def unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


@dataclass(frozen=True, slots=True)
class Principal:
    """Who is calling, and through which login."""

    user: User
    session: UserSession


async def get_current_principal(session: SessionDep, token: SessionCookieDep) -> Principal:
    if token is None:
        raise unauthorized()
    now = utcnow()
    user_session = await session.scalar(
        select(UserSession)
        .options(selectinload(UserSession.user))
        .where(UserSession.token_hash == hash_token(token))
        .where(UserSession.revoked_at.is_(None))
        .where(UserSession.expires_at > now)
    )
    if user_session is None:
        raise unauthorized()
    last_used = user_session.last_used_at
    if last_used is None or now - last_used > LAST_USED_RESOLUTION:
        user_session.last_used_at = now
        await session.commit()
    return Principal(user=user_session.user, session=user_session)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def get_current_user(principal: CurrentPrincipal) -> User:
    return principal.user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
