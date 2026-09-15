from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from alloy_server.config import Settings
from alloy_server.integrations.mail import Mailer
from alloy_server.integrations.storage import ObjectStore

if TYPE_CHECKING:
    from contextlib import AsyncExitStack

    from procrastinate import JobContext
    from sqlalchemy.ext.asyncio import AsyncEngine

KEY = "resources"


@dataclass(frozen=True, slots=True)
class Resources:
    settings: Settings
    session_factory: Callable[[], AsyncSession]
    mailer: Mailer
    object_store: ObjectStore

    def session(self) -> AsyncSession:
        """One per run; commit explicitly, as handlers do."""
        return self.session_factory()


def worker_context(resources: Resources) -> dict[str, Any]:
    """The `additional_context` to start a worker with."""
    return {KEY: resources}


def resources(context: JobContext) -> Resources:
    found: Resources = context.additional_context[KEY]
    return found


async def open_resources(settings: Settings, stack: AsyncExitStack) -> Resources:
    """Every resource, with its teardown on `stack`."""
    # Imported here to avoid an import cycle.
    from alloy_server.db.session import create_database_state  # noqa: PLC0415
    from alloy_server.integrations.mail import create_mailer  # noqa: PLC0415
    from alloy_server.integrations.storage import create_object_store  # noqa: PLC0415

    database = create_database_state(settings)
    engine: AsyncEngine = database["engine"]
    stack.push_async_callback(engine.dispose)
    return Resources(
        settings=settings,
        session_factory=database["session_factory"],
        mailer=create_mailer(settings),
        object_store=await stack.enter_async_context(create_object_store(settings)),
    )


__all__ = ["KEY", "Resources", "open_resources", "resources", "worker_context"]
