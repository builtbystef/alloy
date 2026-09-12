import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta

from alloy_api.integrations.ratelimit.base import Hit


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
