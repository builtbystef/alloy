from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import timedelta

    from fastapi import Response

SESSION_COOKIE = "__Host-session"


def set_session_cookie(response: Response, token: str, ttl: timedelta) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(ttl.total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    # A delete needs the same attributes the browser stored the cookie with.
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
