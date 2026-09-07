"""Shared fixtures.

Tests run against the real PostgreSQL from compose.yaml (or ALLOY_DATABASE_URL).
Each test gets one connection with an open transaction that is rolled back at
the end, so tests never see each other's rows and leave the database as they
found it. Table creation happens inside that transaction too: PostgreSQL DDL is
transactional, so it is rolled back as well.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alloy_api.config import Settings, get_settings
from alloy_api.db import get_session
from alloy_api.main import app
from alloy_api.models import Base

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

    from anyio.from_thread import BlockingPortal


@pytest.fixture
def settings() -> Settings:
    return Settings(app_name="Test API")


@pytest.fixture
def engine(settings: Settings) -> AsyncEngine:
    # NullPool: no pooled connections to leak between event loops.
    return create_async_engine(str(settings.database_url), poolclass=NullPool)


@pytest.fixture
def app_client(settings: Settings) -> Iterator[TestClient]:
    """TestClient with settings overridden but the real database wiring."""
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@dataclass
class Database:
    """The test's transaction, on the event loop the app runs on.

    TestClient runs the app on its own loop (`client.portal`). Async
    connections are bound to the loop that created them, so async code that
    touches `connection` must go through `run`.
    """

    portal: BlockingPortal
    connection: AsyncConnection

    def run[T](self, func: Callable[..., Awaitable[T]], *args: object) -> T:
        return self.portal.call(func, *args)

    def session(self) -> AsyncSession:
        # create_savepoint: commit() releases a savepoint instead of committing
        # the outer transaction, which the fixture rolls back.
        return AsyncSession(
            bind=self.connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """Drop-in for `alloy_api.db.get_session`."""
        async with self.session() as session:
            yield session


async def _begin(engine: AsyncEngine) -> AsyncConnection:
    try:
        connection = await engine.connect()
    except OperationalError as exc:
        pytest.fail(f"PostgreSQL is not reachable at {engine.url}. Run `vp run db:up`. ({exc})")
    await connection.begin()
    await connection.run_sync(Base.metadata.create_all)
    return connection


async def _end(connection: AsyncConnection, engine: AsyncEngine) -> None:
    await connection.rollback()
    await connection.close()
    await engine.dispose()


@pytest.fixture
def db(app_client: TestClient, engine: AsyncEngine) -> Iterator[Database]:
    """One rolled-back transaction; the app's sessions join it."""
    assert app_client.portal is not None
    connection = app_client.portal.call(_begin, engine)
    database = Database(app_client.portal, connection)
    app.dependency_overrides[get_session] = database.get_session
    try:
        yield database
    finally:
        database.run(_end, connection, engine)


@pytest.fixture
def client(app_client: TestClient, db: Database) -> TestClient:  # noqa: ARG001
    """App client whose database work happens in the `db` transaction."""
    return app_client
