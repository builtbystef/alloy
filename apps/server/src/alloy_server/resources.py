"""What every process works with: the settings, the database, the mailer, the
object store, the rate limit counters, and the job queue, opened once by
`build_resources` and passed on from there.

The API's lifespan, the worker, and the tests call `build_resources` with their own
settings. Nothing reads settings or opens a connection at import time.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from procrastinate import App
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from alloy_server.config import Settings
from alloy_server.db.session import create_engine
from alloy_server.integrations.mail import Mailer, create_mailer
from alloy_server.integrations.rate_limit import DatabaseRateLimitStore, RateLimitStore
from alloy_server.integrations.storage import ObjectStore, create_object_store
from alloy_server.jobs import create_app

if TYPE_CHECKING:
    from procrastinate import JobContext
    from procrastinate.connector import BaseConnector

# Where a worker's `additional_context` holds the resources.
KEY = "resources"


@dataclass(frozen=True, slots=True)
class Resources:
    settings: Settings
    engine: AsyncEngine
    # Tests swap in a factory whose sessions join one transaction.
    session_factory: Callable[[], AsyncSession]
    mailer: Mailer
    object_store: ObjectStore
    rate_limit_store: RateLimitStore
    # The job queue: `defer` queues through it and the worker serves it.
    jobs: App

    def session(self) -> AsyncSession:
        """A new session. One per request or job run; commit explicitly."""
        return self.session_factory()


@asynccontextmanager
async def build_resources(
    settings: Settings,
    *,
    mailer: Mailer | None = None,
    object_store: ObjectStore | None = None,
    rate_limit_store: RateLimitStore | None = None,
    jobs_connector: BaseConnector | None = None,
) -> AsyncIterator[Resources]:
    """Open every resource from `settings` and close them on exit. The engine
    connects lazily; the object store and the job queue open their pools here.
    Tests pass doubles: an outbox, an in-memory store and counters, an in-memory
    queue."""
    engine = create_engine(settings)
    # Attributes stay readable after commit; async code cannot lazy-reload them.
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    jobs = create_app(settings, connector=jobs_connector)
    async with AsyncExitStack() as stack:
        stack.push_async_callback(engine.dispose)
        if object_store is None:
            object_store = await stack.enter_async_context(create_object_store(settings))
        await stack.enter_async_context(jobs.open_async())
        yield Resources(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            mailer=create_mailer(settings) if mailer is None else mailer,
            object_store=object_store,
            rate_limit_store=DatabaseRateLimitStore(session_factory)
            if rate_limit_store is None
            else rate_limit_store,
            jobs=jobs,
        )


def worker_context(resources: Resources) -> dict[str, Any]:
    """The `additional_context` to start a worker with."""
    return {KEY: resources}


def resources_of(context: JobContext) -> Resources:
    """The resources the worker running this job was started with."""
    found: Resources = context.additional_context[KEY]
    return found


__all__ = ["KEY", "Resources", "build_resources", "resources_of", "worker_context"]
