"""The request side of an import: the same handshake as attachments. `POST` the
file's name and size for an upload URL, `PUT` the CSV there, then `POST
.../start` to queue the job, which runs `loader.run_import`."""

import uuid
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from alloy_api.core.exceptions import ConflictError, PayloadTooLargeError
from alloy_api.crm.imports.models import Import, ImportStatus
from alloy_api.crm.imports.schemas import ImportRead, ImportUpload
from alloy_api.crm.ownership import fetch_owned
from alloy_api.db.base import utcnow
from alloy_api.integrations.storage.cleanup import storage_prefix

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import CursorResult, Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.config import Settings
    from alloy_api.crm.imports.schemas import ImportCreate
    from alloy_api.integrations.storage import ObjectStore
    from alloy_api.workspaces.deps import Membership

CSV_CONTENT_TYPE = "text/csv"
WITH_REQUESTER = selectinload(Import.requested_by)


def object_key(workspace_id: UUID, import_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}imports/{import_id}"


def too_large(settings: Settings) -> PayloadTooLargeError:
    return PayloadTooLargeError(f"Import files may be at most {settings.import_max_bytes} bytes")


def imports_query(membership: Membership) -> Select[tuple[Import]]:
    """The workspace's imports, newest first, whatever their state."""
    return (
        select(Import)
        .options(WITH_REQUESTER)
        .where(Import.workspace_id == membership.workspace.id)
        .order_by(Import.created_at.desc(), Import.id.desc())
    )


async def get_import(session: AsyncSession, membership: Membership, import_id: UUID) -> Import:
    return await fetch_owned(session, Import, import_id, membership, WITH_REQUESTER)


async def start_upload(
    session: AsyncSession,
    store: ObjectStore,
    settings: Settings,
    membership: Membership,
    body: ImportCreate,
) -> ImportUpload:
    """Create the row and hand out the upload URL for the CSV. Commits.
    `PayloadTooLargeError` when `size` is over the limit."""
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


async def mark_queued(
    session: AsyncSession,
    store: ObjectStore,
    settings: Settings,
    membership: Membership,
    import_id: UUID,
) -> Import:
    """Called after the `PUT`: check the file is there and move the row to `queued`.
    Commits; the caller sends the job. `ConflictError` when the file is not in the
    store yet or the import was already started; `PayloadTooLargeError`, and the
    file is removed, when it is bigger than allowed."""
    record = await get_import(session, membership, import_id)
    if record.status is not ImportStatus.PENDING:
        raise ConflictError("The import has already been started")
    info = await store.head(record.key)
    if info is None:
        raise ConflictError("The file has not been uploaded yet")
    if info.size > settings.import_max_bytes:
        await store.delete(record.key)
        raise too_large(settings)
    # One conditional UPDATE, so of two `start`s at once exactly one queues the job.
    result = await session.execute(
        update(Import)
        .where(Import.id == record.id, Import.status == ImportStatus.PENDING)
        .values(status=ImportStatus.QUEUED, size=info.size)
    )
    if cast("CursorResult[Any]", result).rowcount == 0:
        await session.rollback()
        raise ConflictError("The import has already been started")
    record.status = ImportStatus.QUEUED
    record.size = info.size
    await session.commit()
    return record
