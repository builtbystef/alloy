"""CSV imports of contacts and companies. The same handshake as attachments: `POST`
the file's name and size for an upload URL, `PUT` the CSV there, then `POST
.../start` to send the job. `GET` shows how far it got and what it could not load.
See `alloy_api.crm.importing` for the file format."""

import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.config import SettingsDep
from alloy_api.crm.attachments import storage_prefix
from alloy_api.crm.common import Page, PageOf, fetch_owned, paginate
from alloy_api.crm.models import Import, ImportStatus
from alloy_api.crm.schemas import ImportCreate, ImportRead, ImportUpload
from alloy_api.db import SessionDep
from alloy_api.jobs.imports import run_import_job
from alloy_api.models import utcnow
from alloy_api.storage import ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/imports", tags=["imports"])

CSV_CONTENT_TYPE = "text/csv"
WITH_REQUESTER = selectinload(Import.requested_by)


def object_key(workspace_id: UUID, import_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}imports/{import_id}"


def too_large(settings: SettingsDep) -> HTTPException:
    return HTTPException(
        status.HTTP_413_CONTENT_TOO_LARGE,
        f"Import files may be at most {settings.import_max_bytes} bytes",
    )


@router.get("/")
async def list_imports(
    session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[ImportRead]:
    """Newest first, whatever their state."""
    query = (
        select(Import)
        .options(WITH_REQUESTER)
        .where(Import.workspace_id == membership.workspace.id)
        .order_by(Import.created_at.desc(), Import.id.desc())
    )
    return await paginate(session, query, page, ImportRead)


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
    if body.size > settings.import_max_bytes:
        raise too_large(settings)
    import_id = uuid.uuid7()
    record = Import(
        id=import_id,
        workspace_id=membership.workspace.id,
        kind=body.kind,
        requested_by_user_id=membership.user.id,
        filename=body.filename,
        size=body.size,
        key=object_key(membership.workspace.id, import_id),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record, ["requested_by"])
    return ImportUpload(
        import_=ImportRead.model_validate(record),
        upload_url=await store.upload_url(
            record.key, CSV_CONTENT_TYPE, record.size, settings.storage_url_ttl
        ),
        expires_at=utcnow() + settings.storage_url_ttl,
    )


@router.get("/{import_id}")
async def read_import(import_id: UUID, session: SessionDep, membership: CanReadCrm) -> ImportRead:
    record = await fetch_owned(session, Import, import_id, membership, WITH_REQUESTER)
    return ImportRead.model_validate(record)


@router.post("/{import_id}/start")
async def start_import(
    import_id: UUID,
    session: SessionDep,
    store: ObjectStoreDep,
    settings: SettingsDep,
    membership: CanWriteCrm,
) -> ImportRead:
    """Called after the `PUT`: sends the job. 409 when the file is not in the store
    yet or the import was already started; 413, and the file is removed, when it is
    bigger than allowed."""
    record = await fetch_owned(session, Import, import_id, membership, WITH_REQUESTER)
    if record.status is not ImportStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "The import has already been started")
    info = await store.head(record.key)
    if info is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The file has not been uploaded yet")
    if info.size > settings.import_max_bytes:
        await store.delete(record.key)
        raise too_large(settings)
    record.size = info.size
    record.status = ImportStatus.QUEUED
    await session.commit()
    await run_import_job.kiq(record.id)
    return ImportRead.model_validate(record)
