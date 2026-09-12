import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.core.exceptions import ConflictError, PayloadTooLargeError
from alloy_api.crm.attachments.models import Attachment
from alloy_api.crm.attachments.schemas import AttachmentRead, AttachmentUpload
from alloy_api.crm.companies.models import Company
from alloy_api.crm.contacts.models import Contact
from alloy_api.crm.ownership import fetch_owned, not_found
from alloy_api.db.base import utcnow
from alloy_api.integrations.storage import ObjectStore
from alloy_api.integrations.storage.cleanup import delete_stored, storage_prefix

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute

    from alloy_api.config import Settings
    from alloy_api.crm.attachments.schemas import AttachmentCreate
    from alloy_api.workspaces.deps import Membership

WITH_UPLOADER = selectinload(Attachment.uploaded_by)


def object_key(workspace_id: UUID, attachment_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}attachments/{attachment_id}"


def parent_column(parent: Contact | Company) -> InstrumentedAttribute[UUID | None]:
    return Attachment.contact_id if isinstance(parent, Contact) else Attachment.company_id


@dataclass(frozen=True, slots=True)
class AttachmentStorage:
    """The object store plus the two settings the upload handshake needs from it."""

    store: ObjectStore
    settings: Settings

    @property
    def max_bytes(self) -> int:
        return self.settings.attachment_max_bytes

    def too_large(self) -> PayloadTooLargeError:
        return PayloadTooLargeError(f"Attachments may be at most {self.max_bytes} bytes")

    async def upload_url(self, attachment: Attachment) -> str:
        return await self.store.upload_url(
            attachment.key,
            attachment.content_type,
            attachment.size,
            self.settings.storage_url_ttl,
        )

    async def download_url(self, attachment: Attachment) -> str:
        return await self.store.download_url(
            attachment.key, attachment.filename, self.settings.storage_url_ttl
        )


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
    storage: AttachmentStorage,
    membership: Membership,
    parent: Contact | Company,
    body: AttachmentCreate,
) -> AttachmentUpload:
    """Create the row and hand out the upload URL. Commits. `PayloadTooLargeError`
    when `size` is over the limit."""
    if body.size > storage.max_bytes:
        raise storage.too_large()
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
        attachment=AttachmentRead.model_validate(attachment),
        upload_url=await storage.upload_url(attachment),
        expires_at=utcnow() + storage.settings.storage_url_ttl,
    )


async def complete_upload(
    session: AsyncSession, storage: AttachmentStorage, membership: Membership, attachment_id: UUID
) -> Attachment:
    """Called after the `PUT`. `ConflictError` when the object is not in the store
    yet; `PayloadTooLargeError`, and the object is removed, when it is bigger than
    allowed. Repeating it is harmless. Commits."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership, WITH_UPLOADER)
    if attachment.uploaded_at is None:
        info = await storage.store.head(attachment.key)
        if info is None:
            raise ConflictError("The file has not been uploaded yet")
        if info.size > storage.max_bytes:
            await storage.store.delete(attachment.key)
            raise storage.too_large()
        # The store is the authority on what was actually received.
        attachment.size = info.size
        attachment.content_type = info.content_type
        attachment.uploaded_at = utcnow()
        await session.commit()
    return attachment


async def download_url(
    session: AsyncSession, storage: AttachmentStorage, membership: Membership, attachment_id: UUID
) -> str:
    attachment = await fetch_owned(session, Attachment, attachment_id, membership)
    if attachment.uploaded_at is None:
        raise not_found(Attachment)
    return await storage.download_url(attachment)


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
