from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from alloy_server.integrations.rate_limit.base import Hit
from alloy_server.integrations.rate_limit.models import RateLimitWindow


class DatabaseRateLimitStore:
    """Counters in `rate_limit_windows`, shared by every API instance. Each call is
    its own short transaction, so a hit stands whatever the request then does
    (a failed login rolls its request back, and must still count).

    The database clock decides whether a window has ended: `clock_timestamp()`,
    not `now()`, which is fixed for the transaction.
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def hit(self, key: str, window: timedelta) -> Hit:
        now = func.clock_timestamp()
        ended = RateLimitWindow.expires_at <= now
        statement = insert(RateLimitWindow).values(key=key, count=1, expires_at=now + window)
        statement = statement.on_conflict_do_update(
            index_elements=[RateLimitWindow.key],
            set_={
                "count": case((ended, 1), else_=RateLimitWindow.count + 1),
                "expires_at": case((ended, now + window), else_=RateLimitWindow.expires_at),
            },
        ).returning(RateLimitWindow.count, RateLimitWindow.expires_at, now)
        async with self._session_factory() as session:
            count, expires_at, at = (await session.execute(statement)).one()
            await session.commit()
        return Hit(count=count, retry_after=expires_at - at)

    async def peek(self, key: str) -> Hit:
        statement = (
            select(RateLimitWindow.count, RateLimitWindow.expires_at, func.clock_timestamp())
            .where(RateLimitWindow.key == key)
            .where(RateLimitWindow.expires_at > func.clock_timestamp())
        )
        async with self._session_factory() as session:
            row = (await session.execute(statement)).one_or_none()
        if row is None:
            return Hit(count=0, retry_after=timedelta(0))
        count, expires_at, at = row
        return Hit(count=count, retry_after=expires_at - at)

    async def reset(self, key: str) -> None:
        async with self._session_factory() as session:
            await session.execute(delete(RateLimitWindow).where(RateLimitWindow.key == key))
            await session.commit()
