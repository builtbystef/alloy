import uuid
from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from alloy_server.db.base import utcnow
from alloy_server.integrations.storage.cleanup import delete_stored, storage_prefix
from alloy_server.modules.assistant.models import (
    AssistantConversation,
    AssistantMessage,
    ChatUpload,
)
from alloy_server.shared.exceptions import ConflictError, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.modules.assistant.schemas import ChatUploadCreate
    from alloy_server.modules.crm.attachments.service import AttachmentStorage
    from alloy_server.modules.workspaces.dependencies import Membership


# --- Conversations -----------------------------------------------------------------


def conversations_query(membership: Membership) -> Select[tuple[AssistantConversation]]:
    return (
        select(AssistantConversation)
        .where(AssistantConversation.workspace_id == membership.workspace.id)
        .where(AssistantConversation.user_id == membership.user.id)
        .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc())
    )


async def get_conversation(
    session: AsyncSession, membership: Membership, conversation_id: UUID
) -> AssistantConversation:
    conversation = await session.scalar(
        select(AssistantConversation)
        .where(AssistantConversation.id == conversation_id)
        .where(AssistantConversation.workspace_id == membership.workspace.id)
        .where(AssistantConversation.user_id == membership.user.id)
    )
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return conversation


async def create_conversation(
    session: AsyncSession, membership: Membership
) -> AssistantConversation:
    """A new, empty conversation. An existing one with no messages is returned
    instead, so "New chat" pressed twice does not pile up empty rows. Commits."""
    has_messages = exists().where(AssistantMessage.conversation_id == AssistantConversation.id)
    empty = await session.scalar(
        select(AssistantConversation)
        .where(AssistantConversation.workspace_id == membership.workspace.id)
        .where(AssistantConversation.user_id == membership.user.id)
        .where(~has_messages)
        .order_by(AssistantConversation.created_at.desc())
        .limit(1)
    )
    if empty is not None:
        return empty
    conversation = AssistantConversation(
        workspace_id=membership.workspace.id, user_id=membership.user.id
    )
    session.add(conversation)
    await session.commit()
    return conversation


async def delete_conversation(
    session: AsyncSession, store: ObjectStore, conversation: AssistantConversation
) -> None:
    """Removes the transcript and the chat's files that were never attached to a
    record. Attachments made from the chat stay on their records. Commits."""
    await purge_unattached(session, store, conversation)
    await session.delete(conversation)
    await session.commit()


# --- Uploads -----------------------------------------------------------------------


def upload_key(workspace_id: UUID, upload_id: UUID) -> str:
    return f"{storage_prefix(workspace_id)}chat-uploads/{upload_id}"


async def get_upload(session: AsyncSession, membership: Membership, upload_id: UUID) -> ChatUpload:
    upload = await session.scalar(
        select(ChatUpload)
        .where(ChatUpload.id == upload_id)
        .where(ChatUpload.workspace_id == membership.workspace.id)
        .where(ChatUpload.user_id == membership.user.id)
    )
    if upload is None:
        raise NotFoundError("Upload not found")
    return upload


async def purge_unattached(
    session: AsyncSession, store: ObjectStore, conversation: AssistantConversation
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


async def start_upload(
    session: AsyncSession,
    storage: AttachmentStorage,
    membership: Membership,
    conversation: AssistantConversation,
    body: ChatUploadCreate,
) -> ChatUpload:
    """Commits. The caller hands out the upload URL."""
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
    return upload


async def complete_upload(
    session: AsyncSession, storage: AttachmentStorage, membership: Membership, upload_id: UUID
) -> ChatUpload:
    """Called after the `PUT`. `ConflictError` when the object is not in the store
    yet; `PayloadTooLargeError`, and the object removed, when it is bigger than
    allowed. Repeating it is harmless. Commits."""
    upload = await get_upload(session, membership, upload_id)
    if upload.uploaded_at is None:
        info = await storage.store.head(upload.key)
        if info is None:
            raise ConflictError("The file has not been uploaded yet")
        if info.size > storage.max_bytes:
            await storage.store.delete(upload.key)
            raise storage.too_large()
        upload.size = info.size
        upload.content_type = info.content_type
        upload.uploaded_at = utcnow()
        await session.commit()
    return upload


async def delete_upload(
    session: AsyncSession, store: ObjectStore, membership: Membership, upload_id: UUID
) -> None:
    """Discard a chat upload the user removed before sending: the row and the
    object. `ConflictError` once it has become an attachment, which owns the
    object then. Commits."""
    upload = await get_upload(session, membership, upload_id)
    if upload.attachment_id is not None:
        raise ConflictError("The file is attached to a record")
    key = upload.key
    await session.delete(upload)
    await session.commit()
    await delete_stored(store, keys=[key])
