from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request

from alloy_server.integrations.rate_limit.base import (
    Hit,
    Limit,
    RateLimiter,
    RateLimitStore,
    too_many_requests,
)
from alloy_server.integrations.rate_limit.database import DatabaseRateLimitStore
from alloy_server.integrations.rate_limit.memory import MemoryRateLimitStore

# Routes that take an emailed token. Not against guessing (tokens are 32 random
# bytes): keeps scanners off the database.
TOKEN_PER_IP = Limit("token:ip", 10, timedelta(minutes=1))


async def get_rate_limiter(request: Request) -> RateLimiter:
    store: RateLimitStore = request.state.rate_limit_store
    return RateLimiter(store)


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def client_ip(request: Request) -> str:
    """No socket (a bare ASGI scope in tests) shares one "unknown" counter rather
    than escaping the limit."""
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]


def per_ip(limit: Limit) -> Callable[[Request, RateLimiter], Awaitable[None]]:
    async def dependency(request: Request, limiter: RateLimiterDep) -> None:
        await limiter.hit(limit, client_ip(request))

    return dependency


__all__ = [
    "TOKEN_PER_IP",
    "ClientIp",
    "DatabaseRateLimitStore",
    "Hit",
    "Limit",
    "MemoryRateLimitStore",
    "RateLimitStore",
    "RateLimiter",
    "RateLimiterDep",
    "client_ip",
    "get_rate_limiter",
    "per_ip",
    "too_many_requests",
]
