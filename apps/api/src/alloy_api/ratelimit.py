import logging
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Literal, Protocol

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

if TYPE_CHECKING:
    from alloy_api.config import Settings

log = logging.getLogger(__name__)

RateLimitStore = Literal["redis", "memory"]

KEY_PREFIX = "ratelimit"


@dataclass(frozen=True, slots=True)
class Limit:
    """`limit` hits per `window` on one subject."""

    name: str
    limit: int
    window: timedelta


LOGIN_PER_IP = Limit("login:ip", 20, timedelta(minutes=15))
LOGIN_PER_EMAIL = Limit("login:email", 10, timedelta(minutes=15))
SIGNUP_PER_IP = Limit("signup:ip", 10, timedelta(hours=1))
FORGOT_PASSWORD_PER_IP = Limit("forgot-password:ip", 10, timedelta(hours=1))
FORGOT_PASSWORD_PER_EMAIL = Limit("forgot-password:email", 3, timedelta(hours=1))
RESEND_VERIFICATION_PER_USER = Limit("resend-verification:user", 3, timedelta(hours=1))
# Not against guessing (tokens are 32 random bytes): keeps scanners off the database.
TOKEN_PER_IP = Limit("token:ip", 10, timedelta(minutes=1))
INVITE_ACCEPT_PER_USER = Limit("invite-accept:user", 10, timedelta(minutes=1))


@dataclass(frozen=True, slots=True)
class Hit:
    count: int
    retry_after: timedelta


class RateLimitStoreProtocol(Protocol):
    """`window` only takes effect on the hit that starts a new window."""

    async def hit(self, key: str, window: timedelta) -> Hit: ...
    async def peek(self, key: str) -> Hit: ...
    async def reset(self, key: str) -> None: ...
    async def aclose(self) -> None: ...


class RedisRateLimitStore:
    """`EXPIRE NX` needs Redis 7."""

    def __init__(self, url: str) -> None:
        self._redis = Redis.from_url(url)

    async def hit(self, key: str, window: timedelta) -> Hit:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window, nx=True)
            pipe.pttl(key)
            count, _, ttl_ms = await pipe.execute()
        # -1 means no expiry, which `expire nx` rules out; re-arm anyway so a
        # counter can never get stuck.
        if ttl_ms < 0:
            await self._redis.expire(key, window)
            ttl_ms = int(window.total_seconds() * 1000)
        return Hit(count=int(count), retry_after=timedelta(milliseconds=ttl_ms))

    async def peek(self, key: str) -> Hit:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.get(key)
            pipe.pttl(key)
            value, ttl_ms = await pipe.execute()
        if value is None:
            return Hit(count=0, retry_after=timedelta(0))
        return Hit(count=int(value), retry_after=timedelta(milliseconds=max(0, ttl_ms)))

    async def reset(self, key: str) -> None:
        await self._redis.delete(key)

    async def aclose(self) -> None:
        await self._redis.aclose()


@dataclass(slots=True)
class _Window:
    count: int
    expires_at: float


@dataclass(slots=True)
class MemoryRateLimitStore:
    """Per process, so development and tests only."""

    clock: Callable[[], float] = time.monotonic
    _windows: dict[str, _Window] = field(default_factory=dict)

    def _live(self, key: str) -> _Window | None:
        window = self._windows.get(key)
        if window is None:
            return None
        if window.expires_at <= self.clock():
            del self._windows[key]
            return None
        return window

    async def hit(self, key: str, window: timedelta) -> Hit:
        now = self.clock()
        live = self._live(key)
        if live is None:
            live = self._windows[key] = _Window(count=0, expires_at=now + window.total_seconds())
        live.count += 1
        return Hit(count=live.count, retry_after=timedelta(seconds=live.expires_at - now))

    async def peek(self, key: str) -> Hit:
        live = self._live(key)
        if live is None:
            return Hit(count=0, retry_after=timedelta(0))
        return Hit(count=live.count, retry_after=timedelta(seconds=live.expires_at - self.clock()))

    async def reset(self, key: str) -> None:
        self._windows.pop(key, None)

    async def aclose(self) -> None:
        self._windows.clear()


def create_rate_limit_store(settings: Settings) -> RateLimitStoreProtocol:
    match settings.rate_limit_store:
        case "redis":
            return RedisRateLimitStore(str(settings.redis_url))
        case "memory":
            return MemoryRateLimitStore()


def too_many_requests(retry_after: timedelta) -> HTTPException:
    seconds = max(1, math.ceil(retry_after.total_seconds()))
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Too many attempts. Try again later.",
        headers={"Retry-After": str(seconds)},
    )


@dataclass(frozen=True, slots=True)
class Limiter:
    """Raises 429 past the limit."""

    store: RateLimitStoreProtocol

    @staticmethod
    def key(limit: Limit, subject: str) -> str:
        return f"{KEY_PREFIX}:{limit.name}:{subject}"

    async def hit(self, limit: Limit, subject: str) -> None:
        hit = await self.store.hit(self.key(limit, subject), limit.window)
        if hit.count > limit.limit:
            self._refuse(limit, subject, hit.retry_after)

    async def check(self, limit: Limit, subject: str) -> None:
        """Does not count. For failure-only limits: `check` first, `hit` on failure,
        `reset` on success."""
        standing = await self.store.peek(self.key(limit, subject))
        if standing.count >= limit.limit:
            self._refuse(limit, subject, standing.retry_after)

    async def reset(self, limit: Limit, subject: str) -> None:
        await self.store.reset(self.key(limit, subject))

    @staticmethod
    def _refuse(limit: Limit, subject: str, retry_after: timedelta) -> None:
        log.warning("Rate limit %s hit by %s", limit.name, subject)
        raise too_many_requests(retry_after)


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
    "FORGOT_PASSWORD_PER_EMAIL",
    "FORGOT_PASSWORD_PER_IP",
    "INVITE_ACCEPT_PER_USER",
    "LOGIN_PER_EMAIL",
    "LOGIN_PER_IP",
    "RESEND_VERIFICATION_PER_USER",
    "SIGNUP_PER_IP",
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
]
