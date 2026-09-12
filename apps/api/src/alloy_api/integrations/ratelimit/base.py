import logging
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from alloy_api.core.exceptions import RateLimitedError

log = logging.getLogger(__name__)

KEY_PREFIX = "ratelimit"


@dataclass(frozen=True, slots=True)
class Limit:
    """`limit` hits per `window` on one subject."""

    name: str
    limit: int
    window: timedelta


@dataclass(frozen=True, slots=True)
class Hit:
    count: int
    retry_after: timedelta


class RateLimitStoreProtocol(Protocol):
    """What the limiter needs from a counter store. Implement it to add a backend.

    `window` only takes effect on the hit that starts a new window.
    """

    async def hit(self, key: str, window: timedelta) -> Hit: ...
    async def peek(self, key: str) -> Hit: ...
    async def reset(self, key: str) -> None: ...
    async def aclose(self) -> None: ...


def too_many_requests(retry_after: timedelta) -> RateLimitedError:
    seconds = max(1, math.ceil(retry_after.total_seconds()))
    return RateLimitedError(
        "Too many attempts. Try again later.", headers={"Retry-After": str(seconds)}
    )


@dataclass(frozen=True, slots=True)
class Limiter:
    """Raises `RateLimitedError` (a 429 with `Retry-After`) past the limit."""

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
