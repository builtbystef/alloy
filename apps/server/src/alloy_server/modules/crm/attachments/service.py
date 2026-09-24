import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_server.db.base import utcnow
from alloy_server.integrations.storage.cleanup import delete_stored, storage_prefix
from alloy_server.modules.crm.attachments.models import Attachment
from alloy_server.modules.crm.attachments.schemas import AttachmentResponse, AttachmentUpload
from alloy_server.modules.crm.companies.models import Company
from alloy_server.modules.crm.contacts.models import Contact
from alloy_server.modules.crm.ownership import fetch_owned, not_found

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute

    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.integrations.storage.uploads import UploadStorage
    from alloy_server.modules.crm.attachments.schemas import AttachmentCreate
    from alloy_server.modules.workspaces.dependencies import Membership

WITH_UPLOADER = selectinload(Attachment.uploaded_by)


def object_key(workspace_id: UUID, attachment_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}attachments/{attachment_id}"


def parent_column(parent: Contact | Company) -> InstrumentedAttribute[UUID | None]:
    return Attachment.contact_id if isinstance(parent, Contact) else Attachment.company_id


def attachments_query(parent: Contact | Company) -> Select[tuple[Attachment]]:
    return (
        select(Attachment)
        .options(WITH_UPLOADER)
        .where(parent_column(parent) == parent.id)
        .where(Attachment.uploaded_at.is_not(None))
        .order_by(Attachment.uploaded_at.desc(), Attachment.id.desc())
    )


async def start_upload(
    session: AsyncSession,
    storage: UploadStorage,
    membership: Membership,
    parent: Contact | Company,
    body: AttachmentCreate,
) -> AttachmentUpload:
    """Create the row and hand out the upload URL. Commits. `PayloadTooLargeError`
    when `size` is over the limit."""
    storage.check_size(body.size)
    attachment_id = uuid.uuid7()
    attachment = Attachment(
        id=attachment_id,
        workspace_id=membership.workspace.id,
        contact_id=parent.id if isinstance(parent, Contact) else None,
        company_id=parent.id if isinstance(parent, Company) else None,
        uploaded_by_user_id=membership.user.id,
        filename=body.filename,
        content_type=body.content_type,
        size=body.size,
        key=object_key(membership.workspace.id, attachment_id),
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment, ["uploaded_by"])
    return AttachmentUpload(
        attachment=AttachmentResponse.model_validate(attachment),
        upload_url=await storage.upload_url(
            attachment.key, attachment.content_type, attachment.size
        ),
        expires_at=storage.expires_at(),
    )


async def complete_upload(
    session: AsyncSession, storage: UploadStorage, membership: Membership, attachment_id: UUID
) -> Attachment:
    """Called after the `PUT`. `ConflictError` when the object is not in the store
    yet; `PayloadTooLargeError`, and the object is removed, when it is bigger than
    allowed. Repeating it is harmless. Commits."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership, WITH_UPLOADER)
    if attachment.uploaded_at is None:
        info = await storage.verify(attachment.key)
        attachment.size = info.size
        attachment.content_type = info.content_type
        attachment.uploaded_at = utcnow()
        await session.commit()
    return attachment


async def download_url(
    session: AsyncSession, storage: UploadStorage, membership: Membership, attachment_id: UUID
) -> str:
    attachment = await fetch_owned(session, Attachment, attachment_id, membership)
    if attachment.uploaded_at is None:
        raise not_found(Attachment)
    return await storage.download_url(attachment.key, attachment.filename)


async def delete_attachment(
    session: AsyncSession, store: ObjectStore, membership: Membership, attachment_id: UUID
) -> Attachment:
    """Removes the row and commits, then the file from the store."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership)
    await session.delete(attachment)
    await session.commit()
    await delete_stored(store, keys=[attachment.key])
    return attachment


async def delete_with_attachments(
    session: AsyncSession, store: ObjectStore, parent: Contact | Company
) -> None:
    """Delete a contact or company and commit, then remove the stored files of the
    attachments that went with it."""
    keys = list(
        await session.scalars(select(Attachment.key).where(parent_column(parent) == parent.id))
    )
    await session.delete(parent)
    await session.commit()
    await delete_stored(store, keys=keys)
