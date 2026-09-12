"""Fixed-window rate limiting. Each feature owns its `Limit` constants. Routes
attach `per_ip(limit)` as a dependency, or use `LimiterDep` when the subject is
in the body or only failures should count."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import Depends, Request

from alloy_api.integrations.ratelimit.base import (
    Hit,
    Limit,
    Limiter,
    RateLimitStoreProtocol,
    too_many_requests,
)
from alloy_api.integrations.ratelimit.memory import MemoryRateLimitStore
from alloy_api.integrations.ratelimit.redis import RedisRateLimitStore

if TYPE_CHECKING:
    from alloy_api.config import Settings

RateLimitStore = Literal["redis", "memory"]

# Routes that take an emailed token. Not against guessing (tokens are 32 random
# bytes): keeps scanners off the database.
TOKEN_PER_IP = Limit("token:ip", 10, timedelta(minutes=1))


def create_rate_limit_store(settings: Settings) -> RateLimitStoreProtocol:
    match settings.rate_limit_store:
        case "redis":
            return RedisRateLimitStore(str(settings.redis_url), settings.redis_timeout)
        case "memory":
            return MemoryRateLimitStore()


async def get_limiter(request: Request) -> Limiter:
    store: RateLimitStoreProtocol = request.state.rate_limit_store
    return Limiter(store)


LimiterDep = Annotated[Limiter, Depends(get_limiter)]


def client_ip(request: Request) -> str:
    """No socket (a bare ASGI scope in tests) shares one "unknown" counter rather
    than escaping the limit."""
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]


def per_ip(limit: Limit) -> Callable[[Request, Limiter], Awaitable[None]]:
    async def dependency(request: Request, limiter: LimiterDep) -> None:
        await limiter.hit(limit, client_ip(request))

    return dependency


__all__ = [
    "TOKEN_PER_IP",
    "ClientIp",
    "Hit",
    "Limit",
    "Limiter",
    "LimiterDep",
    "MemoryRateLimitStore",
    "RateLimitStore",
    "RateLimitStoreProtocol",
    "RedisRateLimitStore",
    "client_ip",
    "create_rate_limit_store",
    "get_limiter",
    "per_ip",
    "too_many_requests",
]
