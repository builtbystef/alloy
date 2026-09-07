import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.config import SettingsDep
from alloy_api.crm.common import Page, fetch_owned, not_found
from alloy_api.crm.models import Attachment, Company, Contact
from alloy_api.crm.schemas import AttachmentCreate, AttachmentRead, AttachmentUpload
from alloy_api.db import SessionDep
from alloy_api.models import utcnow
from alloy_api.storage import ObjectStore, ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute

    from alloy_api.config import Settings
    from alloy_api.workspaces.deps import Membership

router = APIRouter(tags=["attachments"])

WITH_UPLOADER = selectinload(Attachment.uploaded_by)


def storage_prefix(workspace_id: UUID) -> str:
    """Every object of a workspace lives under this, so deleting the workspace can
    clear its storage by prefix."""
    return f"workspaces/{workspace_id}/"


def object_key(workspace_id: UUID, attachment_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}attachments/{attachment_id}"


def parent_column(parent: Contact | Company) -> InstrumentedAttribute[UUID | None]:
    return Attachment.contact_id if isinstance(parent, Contact) else Attachment.company_id


@dataclass(frozen=True, slots=True)
class AttachmentStorage:
    """The object store plus the two settings the attachment routes need from it."""

    store: ObjectStore
    settings: Settings

    @property
    def max_bytes(self) -> int:
        return self.settings.attachment_max_bytes

    def too_large(self) -> HTTPException:
        return HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Attachments may be at most {self.max_bytes} bytes",
        )

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


def get_attachment_storage(store: ObjectStoreDep, settings: SettingsDep) -> AttachmentStorage:
    return AttachmentStorage(store, settings)


StorageDep = Annotated[AttachmentStorage, Depends(get_attachment_storage)]


async def delete_objects(
    session: AsyncSession, store: ObjectStore, parent: Contact | Company
) -> None:
    """Remove the stored files of every attachment on a contact or company, before
    the rows go with their parent."""
    query = select(Attachment.key).where(parent_column(parent) == parent.id)
    for key in await session.scalars(query):
        await store.delete(key)


async def _list(
    session: AsyncSession, parent: Contact | Company, page: Page
) -> list[AttachmentRead]:
    query = (
        select(Attachment)
        .options(WITH_UPLOADER)
        .where(parent_column(parent) == parent.id)
        .where(Attachment.uploaded_at.is_not(None))
        .order_by(Attachment.uploaded_at.desc(), Attachment.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    return [AttachmentRead.model_validate(a) for a in await session.scalars(query)]


async def _create(
    session: AsyncSession,
    storage: AttachmentStorage,
    membership: Membership,
    parent: Contact | Company,
    body: AttachmentCreate,
) -> AttachmentUpload:
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


@router.get("/contacts/{contact_id}/attachments")
async def list_contact_attachments(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> list[AttachmentRead]:
    """Newest first. Files whose upload never completed are left out."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    return await _list(session, contact, page)


@router.post("/contacts/{contact_id}/attachments", status_code=status.HTTP_201_CREATED)
async def create_contact_attachment(
    contact_id: UUID,
    body: AttachmentCreate,
    session: SessionDep,
    storage: StorageDep,
    membership: CanWriteCrm,
) -> AttachmentUpload:
    """Start an upload: the row is created and an upload URL returned. 413 when
    `size` is over the limit."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    return await _create(session, storage, membership, contact, body)


@router.get("/companies/{company_id}/attachments")
async def list_company_attachments(
    company_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> list[AttachmentRead]:
    """Newest first. Files whose upload never completed are left out."""
    company = await fetch_owned(session, Company, company_id, membership)
    return await _list(session, company, page)


@router.post("/companies/{company_id}/attachments", status_code=status.HTTP_201_CREATED)
async def create_company_attachment(
    company_id: UUID,
    body: AttachmentCreate,
    session: SessionDep,
    storage: StorageDep,
    membership: CanWriteCrm,
) -> AttachmentUpload:
    """Start an upload: the row is created and an upload URL returned. 413 when
    `size` is over the limit."""
    company = await fetch_owned(session, Company, company_id, membership)
    return await _create(session, storage, membership, company, body)


@router.post("/attachments/{attachment_id}/complete")
async def complete_attachment(
    attachment_id: UUID, session: SessionDep, storage: StorageDep, membership: CanWriteCrm
) -> AttachmentRead:
    """Called after the `PUT`. 409 when the object is not in the store yet; 413, and
    the object is removed, when it is bigger than allowed. Repeating it is harmless."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership, WITH_UPLOADER)
    if attachment.uploaded_at is None:
        info = await storage.store.head(attachment.key)
        if info is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "The file has not been uploaded yet")
        if info.size > storage.max_bytes:
            await storage.store.delete(attachment.key)
            raise storage.too_large()
        # The store is the authority on what was actually received.
        attachment.size = info.size
        attachment.content_type = info.content_type
        attachment.uploaded_at = utcnow()
        await session.commit()
    return AttachmentRead.model_validate(attachment)


@router.get("/attachments/{attachment_id}/download", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def download_attachment(
    attachment_id: UUID, session: SessionDep, storage: StorageDep, membership: CanReadCrm
) -> RedirectResponse:
    """Redirects to a short-lived URL that serves the file as a download."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership)
    if attachment.uploaded_at is None:
        raise not_found(Attachment)
    return RedirectResponse(
        await storage.download_url(attachment), status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: UUID, session: SessionDep, storage: StorageDep, membership: CanWriteCrm
) -> Response:
    """Removes the file from the store, then the row."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership)
    await storage.store.delete(attachment.key)
    await session.delete(attachment)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
