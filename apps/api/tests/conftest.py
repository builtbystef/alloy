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
from alloy_api.mail import Email, get_mailer
from alloy_api.main import app
from alloy_api.models import Base

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping

    from anyio.from_thread import BlockingPortal


@pytest.fixture
def settings() -> Settings:
    return Settings(app_name="Test API")


@pytest.fixture
def engine(settings: Settings) -> AsyncEngine:
    # NullPool: nothing pooled across event loops.
    return create_async_engine(str(settings.database_url), poolclass=NullPool)


class Outbox(list[Email]):
    """A `Mailer` that keeps what it is asked to send."""

    async def send(self, email: Email) -> None:
        self.append(email)


@pytest.fixture
def outbox() -> Outbox:
    return Outbox()


@pytest.fixture
def app_client(settings: Settings, outbox: Outbox) -> Iterator[TestClient]:
    """Settings and mailer overridden, real database wiring."""
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mailer] = lambda: outbox
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


PASSWORD = "correct horse battery"  # noqa: S105 - a fixture, not a secret


def signup(client: TestClient, email: str) -> dict[str, str]:
    """Create a user and return a `Cookie` header for them.

    Explicit headers, not the client's cookie jar, so two users can share one client.
    """
    response = client.post("/auth/signup", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    token = response.cookies[SESSION_COOKIE]
    client.cookies.clear()
    return {"Cookie": f"{SESSION_COOKIE}={token}"}


@dataclass
class Actor:
    """A logged-in user acting inside one workspace.

    `get`/`post`/... take a path relative to the workspace (`/contacts/`), send the
    user's cookie, and return the response. `ws()` builds the absolute path.
    """

    client: TestClient
    email: str
    headers: dict[str, str]
    workspace: str

    def ws(self, path: str = "") -> str:
        return f"/workspaces/{self.workspace}{path}"

    def get(self, path: str, *, params: Mapping[str, str | int] | None = None):
        return self.client.get(self.ws(path), params=params, headers=self.headers)

    def post(self, path: str, *, json: object = None):
        return self.client.post(self.ws(path), json=json, headers=self.headers)

    def patch(self, path: str, *, json: object = None):
        return self.client.patch(self.ws(path), json=json, headers=self.headers)

    def delete(self, path: str):
        return self.client.delete(self.ws(path), headers=self.headers)


def actor(client: TestClient, email: str) -> Actor:
    """Sign up and act in the workspace signup created."""
    headers = signup(client, email)
    workspaces = client.get("/workspaces/", headers=headers).json()
    assert len(workspaces) == 1
    return Actor(client, email, headers, workspaces[0]["id"])


@pytest.fixture
def new_login(client: TestClient) -> Callable[[str], dict[str, str]]:
    """`signup` as a fixture, for tests that need a third user."""
    return lambda email: signup(client, email)


@pytest.fixture
def new_actor(client: TestClient) -> Callable[[str], Actor]:
    """`actor` as a fixture, for tests that need a third user."""
    return lambda email: actor(client, email)


@pytest.fixture
def join(client: TestClient, outbox: Outbox) -> Callable[[Actor, str, str], Actor]:
    """Sign `email` up and seat them in `host`'s workspace with `role`, via an invitation."""

    def join(host: Actor, email: str, role: str) -> Actor:
        guest = actor(client, email)
        invite = host.post("/invites", json={"email": email, "role": role})
        assert invite.status_code == 201, invite.text
        token = outbox[-1].text.split("/invites/")[1].split()[0]
        accepted = client.post(f"/invites/{token}/accept", headers=guest.headers)
        assert accepted.status_code == 200, accepted.text
        return Actor(client, email, guest.headers, host.workspace)

    return join


@pytest.fixture
def alice(client: TestClient) -> Actor:
    return actor(client, "alice@example.com")


@pytest.fixture
def bob(client: TestClient) -> Actor:
    """A second user with a workspace of their own, for data isolation tests."""
    return actor(client, "bob@example.com")
