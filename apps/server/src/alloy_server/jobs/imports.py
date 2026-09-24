from typing import TYPE_CHECKING
from uuid import UUID

from alloy_server.jobs.app import defer, task
from alloy_server.jobs.resources import Resources
from alloy_server.modules.crm.imports.loader import run_import

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@task("imports.run")
async def run_import_job(res: Resources, import_id: str) -> None:
    async with res.session() as session:
        await run_import(session, res.object_store, UUID(import_id))


async def queue_import(session: AsyncSession, import_id: UUID) -> int:
    """Loads the import's CSV. Queued in `session`'s transaction, with the row
    going to `queued`."""
    return await defer(session, run_import_job, import_id=str(import_id))
