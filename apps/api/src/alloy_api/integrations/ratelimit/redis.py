from datetime import timedelta

from redis.asyncio import Redis

from alloy_api.integrations.ratelimit.base import Hit


class RedisRateLimitStore:
    """Counters shared by every API instance. `EXPIRE NX` needs Redis 7. `timeout`
    bounds every call: this runs on the login and signup paths, which must not
    hang when Redis does."""

    def __init__(self, url: str, timeout: timedelta = timedelta(seconds=2)) -> None:
        seconds = timeout.total_seconds()
        self._redis = Redis.from_url(url, socket_connect_timeout=seconds, socket_timeout=seconds)

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
