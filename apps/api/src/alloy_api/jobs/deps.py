"""What a task can ask for, resolved from the broker state.

The worker has no request, so the FastAPI `*Dep` aliases do not apply. The
resources are put on `TaskiqState` once per process by `configure` (the worker
does it at startup; the API does it in its lifespan when the broker is
in-memory; the tests do it with their transaction and doubles), and a task
declares them as defaults: `session: AsyncSession = TaskiqDepends(get_session)`.

Annotations here are read at runtime by taskiq-dependencies, so nothing they
name may sit in a `TYPE_CHECKING` block.
"""

from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends, TaskiqState

from alloy_api.config import Settings
from alloy_api.mail import Mailer
from alloy_api.storage import ObjectStore

if TYPE_CHECKING:
    from contextlib import AsyncExitStack

    from sqlalchemy.ext.asyncio import AsyncEngine


def configure(
    state: TaskiqState,
    *,
    settings: Settings,
    session_factory: Callable[[], AsyncSession],
    mailer: Mailer,
    object_store: ObjectStore,
) -> None:
    state.settings = settings
    state.session_factory = session_factory
    state.mailer = mailer
    state.object_store = object_store


async def open_resources(state: TaskiqState, settings: Settings, stack: AsyncExitStack) -> None:
    """Build every resource from `settings` and register their teardown on `stack`.
    What the worker process does at startup."""
    from alloy_api.db import create_database_state  # noqa: PLC0415 - avoids an import cycle
    from alloy_api.mail import create_mailer  # noqa: PLC0415
    from alloy_api.storage import create_object_store  # noqa: PLC0415

    database = create_database_state(settings)
    engine: AsyncEngine = database["engine"]
    stack.push_async_callback(engine.dispose)
    configure(
        state,
        settings=settings,
        session_factory=database["session_factory"],
        mailer=create_mailer(settings),
        object_store=await stack.enter_async_context(create_object_store(settings)),
    )


def get_settings(context: Context = TaskiqDepends()) -> Settings:
    settings: Settings = context.state.settings
    return settings


async def get_session(context: Context = TaskiqDepends()) -> AsyncGenerator[AsyncSession]:
    """One session per task run; commit explicitly, as handlers do."""
    factory: Callable[[], AsyncSession] = context.state.session_factory
    async with factory() as session:
        yield session


def get_mailer(context: Context = TaskiqDepends()) -> Mailer:
    mailer: Mailer = context.state.mailer
    return mailer


def get_object_store(context: Context = TaskiqDepends()) -> ObjectStore:
    store: ObjectStore = context.state.object_store
    return store
