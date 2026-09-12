from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from alloy_server.crm.imports.loader import run_import
from alloy_server.integrations.storage import ObjectStore
from alloy_server.jobs.broker import broker
from alloy_server.jobs.deps import get_object_store, get_session


@broker.task(task_name="imports.run")
async def run_import_job(
    import_id: UUID,
    session: AsyncSession = TaskiqDepends(get_session),
    store: ObjectStore = TaskiqDepends(get_object_store),
) -> None:
    await run_import(session, store, import_id)
