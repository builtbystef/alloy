"""Task dependencies, resolved from the broker state that `configure` fills.

taskiq-dependencies reads the annotations here at runtime, so nothing they
name may sit in a `TYPE_CHECKING` block.
"""

from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends, TaskiqState

from alloy_server.config import Settings
from alloy_server.integrations.mail import Mailer
from alloy_server.integrations.storage import ObjectStore

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
    """The worker's startup: every resource, with its teardown on `stack`."""
    # Imported here to avoid an import cycle.
    from alloy_server.db.session import create_database_state  # noqa: PLC0415
    from alloy_server.integrations.mail import create_mailer  # noqa: PLC0415
    from alloy_server.integrations.storage import create_object_store  # noqa: PLC0415

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
