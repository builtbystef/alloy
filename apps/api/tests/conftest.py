"""Tests use the real PostgreSQL. Each test runs in one transaction that is rolled
back at the end, DDL included, so the database is left as it was found.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alloy_api.auth.cookies import SESSION_COOKIE
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
    # NullPool: nothing pooled across event loops.
    return create_async_engine(str(settings.database_url), poolclass=NullPool)


@pytest.fixture
def app_client(settings: Settings) -> Iterator[TestClient]:
    """Settings overridden, real database wiring."""
    app.dependency_overrides[get_settings] = lambda: settings
    # https: the session cookie is `Secure`, and httpx's jar only sends it over https.
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@dataclass
class Database:
    """The test transaction. It lives on the app's event loop, so use `run` to reach it."""

    portal: BlockingPortal
    connection: AsyncConnection

    def run[T](self, func: Callable[..., Awaitable[T]], *args: object) -> T:
        return self.portal.call(func, *args)

    def session(self) -> AsyncSession:
        # commit() releases a savepoint; the fixture rolls back the outer transaction.
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
    """The app's sessions join this transaction."""
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
    """`app_client` with the `db` transaction."""
    return app_client


def signup(client: TestClient, email: str) -> dict[str, str]:
    """Create a user and return a `Cookie` header for them.

    Explicit headers, not the client's cookie jar, so two users can share one client.
    """
    response = client.post(
        "/auth/signup", json={"email": email, "password": "correct horse battery"}
    )
    assert response.status_code == 201, response.text
    token = response.cookies[SESSION_COOKIE]
    client.cookies.clear()
    return {"Cookie": f"{SESSION_COOKIE}={token}"}


@pytest.fixture
def alice(client: TestClient) -> dict[str, str]:
    return signup(client, "alice@example.com")


@pytest.fixture
def bob(client: TestClient) -> dict[str, str]:
    """A second user, for data isolation tests."""
    return signup(client, "bob@example.com")
