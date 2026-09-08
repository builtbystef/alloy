from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from alloy_api.crm.importing import run_import
from alloy_api.jobs.broker import broker
from alloy_api.jobs.deps import get_object_store, get_session
from alloy_api.storage import ObjectStore


@broker.task(task_name="imports.run")
async def run_import_job(
    import_id: UUID,
    session: AsyncSession = TaskiqDepends(get_session),
    store: ObjectStore = TaskiqDepends(get_object_store),
) -> None:
    await run_import(session, store, import_id)
