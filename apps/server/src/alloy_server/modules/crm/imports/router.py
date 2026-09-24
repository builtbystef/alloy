from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from alloy_server.config import SettingsDep
from alloy_server.db.session import SessionDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.modules.crm.imports import service
from alloy_server.modules.crm.imports.schemas import ImportCreate, ImportResponse, ImportUpload
from alloy_server.modules.crm.pagination import Page, PageOf, paginate
from alloy_server.modules.workspaces.dependencies import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/")
async def list_imports(
    session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[ImportResponse]:
    """Newest first, whatever their state."""
    return await paginate(session, service.imports_query(membership), page, ImportResponse)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_import(
    body: ImportCreate,
    session: SessionDep,
    store: ObjectStoreDep,
    settings: SettingsDep,
    membership: CanWriteCrm,
) -> ImportUpload:
    """Start an import: the row is created and an upload URL for the CSV returned.
    413 when `size` is over the limit."""
    return await service.start_upload(session, store, settings, membership, body)


@router.get("/{import_id}")
async def read_import(
    import_id: UUID, session: SessionDep, membership: CanReadCrm
) -> ImportResponse:
    return ImportResponse.model_validate(await service.get_import(session, membership, import_id))


@router.post("/{import_id}/start")
async def start_import(
    import_id: UUID,
    session: SessionDep,
    store: ObjectStoreDep,
    settings: SettingsDep,
    membership: CanWriteCrm,
) -> ImportResponse:
    """Called after the `PUT`: queues the job. 409 when the file is not in the store
    yet or the import was already started; 413, and the file is removed, when it is
    bigger than allowed."""
    record = await service.mark_queued(session, store, settings, membership, import_id)
    return ImportResponse.model_validate(record)
