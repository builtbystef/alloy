"""Database engine and per-request sessions.

The engine is created once in the app lifespan (see main.py) and shared by
every request through the lifespan state. Handlers take `SessionDep` and get a
fresh `AsyncSession`; the session is closed when the request ends. Commit
explicitly in the handler (`await session.commit()`), nothing commits for you.
"""

from typing import TYPE_CHECKING, Annotated, TypedDict

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from alloy_api.config import Settings


class DatabaseState(TypedDict):
    """What the lifespan puts on `request.state`."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(str(settings.database_url), echo=settings.database_echo)


def create_database_state(settings: Settings) -> DatabaseState:
    engine = create_engine(settings)
    # expire_on_commit=False: attributes stay readable after commit instead of
    # triggering a lazy reload, which cannot happen implicitly in async code.
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return DatabaseState(engine=engine, session_factory=session_factory)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.state.session_factory
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
