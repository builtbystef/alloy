from typing import TYPE_CHECKING, Annotated, TypedDict

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alloy_api import telemetry

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from alloy_api.config import Settings


class DatabaseState(TypedDict):
    """What the lifespan puts on `request.state`."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


def create_engine(settings: Settings) -> AsyncEngine:
    engine = create_async_engine(str(settings.database_url), echo=settings.database_echo)
    if telemetry.enabled(settings):
        telemetry.instrument_engine(engine)
    return engine


def create_database_state(settings: Settings) -> DatabaseState:
    engine = create_engine(settings)
    # Attributes stay readable after commit; async code cannot lazy-reload them.
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return DatabaseState(engine=engine, session_factory=session_factory)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.state.session_factory
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
