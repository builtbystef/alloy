import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from alloy_api.agent.models import AgentConversation, ChatUpload
from alloy_api.agent.schemas import ChatUploadCreate, ChatUploadRead, ChatUploadTicket
from alloy_api.crm.attachments import StorageDep
from alloy_api.db import SessionDep
from alloy_api.models import utcnow
from alloy_api.storage.cleanup import delete_stored, storage_prefix
from alloy_api.workspaces.deps import CanReadCrm

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.storage import ObjectStore
    from alloy_api.workspaces.deps import Membership

router = APIRouter(tags=["agent"])


def upload_key(workspace_id: UUID, upload_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}chat-uploads/{upload_id}"


def upload_not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Upload not found")


async def fetch_conversation(
    session: AsyncSession, membership: Membership, conversation_id: UUID
) -> AgentConversation:
    """The caller's own conversation in this workspace; 404 otherwise."""
    conversation = await session.scalar(
        select(AgentConversation)
        .where(AgentConversation.id == conversation_id)
        .where(AgentConversation.workspace_id == membership.workspace.id)
        .where(AgentConversation.user_id == membership.user.id)
    )
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


async def fetch_upload(
    session: AsyncSession, membership: Membership, upload_id: UUID
) -> ChatUpload:
    upload = await session.scalar(
        select(ChatUpload)
        .where(ChatUpload.id == upload_id)
        .where(ChatUpload.workspace_id == membership.workspace.id)
        .where(ChatUpload.user_id == membership.user.id)
    )
    if upload is None:
        raise upload_not_found()
    return upload


async def purge_unattached(
    session: AsyncSession, store: ObjectStore, conversation: AgentConversation
) -> None:
    """Remove the conversation's uploads that never became attachments, rows and
    objects. Attached ones stay: the attachment owns the object now. Commits."""
    uploads = list(
        await session.scalars(
            select(ChatUpload)
            .where(ChatUpload.conversation_id == conversation.id)
            .where(ChatUpload.attachment_id.is_(None))
        )
    )
    keys = [u.key for u in uploads]
    for upload in uploads:
        await session.delete(upload)
    await session.commit()
    await delete_stored(store, keys=keys)


@router.post("/conversations/{conversation_id}/uploads", status_code=status.HTTP_201_CREATED)
async def create_upload(
    conversation_id: UUID,
    body: ChatUploadCreate,
    session: SessionDep,
    storage: StorageDep,
    membership: CanReadCrm,
) -> ChatUploadTicket:
    """Start a chat upload: the row is created and an upload URL returned. Same size
    limit as attachments; 413 above it."""
    conversation = await fetch_conversation(session, membership, conversation_id)
    if body.size > storage.max_bytes:
        raise storage.too_large()
    upload_id = uuid.uuid7()
    upload = ChatUpload(
        id=upload_id,
        workspace_id=membership.workspace.id,
        user_id=membership.user.id,
        conversation_id=conversation.id,
        filename=body.filename,
        content_type=body.content_type,
        size=body.size,
        key=upload_key(membership.workspace.id, upload_id),
        created_at=utcnow(),
    )
    session.add(upload)
    await session.commit()
    return ChatUploadTicket(
        upload=ChatUploadRead.model_validate(upload),
        upload_url=await storage.store.upload_url(
            upload.key, upload.content_type, upload.size, storage.settings.storage_url_ttl
        ),
        expires_at=utcnow() + storage.settings.storage_url_ttl,
    )


@router.post("/uploads/{upload_id}/complete")
async def complete_upload(
    upload_id: UUID, session: SessionDep, storage: StorageDep, membership: CanReadCrm
) -> ChatUploadRead:
    """Called after the `PUT`. 409 when the object is not in the store yet; 413, and
    the object removed, when it is bigger than allowed. Repeating it is harmless."""
    upload = await fetch_upload(session, membership, upload_id)
    if upload.uploaded_at is None:
        info = await storage.store.head(upload.key)
        if info is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "The file has not been uploaded yet")
        if info.size > storage.max_bytes:
            await storage.store.delete(upload.key)
            raise storage.too_large()
        upload.size = info.size
        upload.content_type = info.content_type
        upload.uploaded_at = utcnow()
        await session.commit()
    return ChatUploadRead.model_validate(upload)


@router.delete("/uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: UUID, session: SessionDep, storage: StorageDep, membership: CanReadCrm
) -> None:
    """Discard a chat upload the user removed before sending: the row and the
    object. 409 once it has become an attachment, which owns the object then."""
    upload = await fetch_upload(session, membership, upload_id)
    if upload.attachment_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The file is attached to a record")
    key = upload.key
    await session.delete(upload)
    await session.commit()
    await delete_stored(storage.store, keys=[key])
