import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from alloy_server.db.base import utcnow
from alloy_server.integrations.storage.cleanup import delete_stored, storage_prefix
from alloy_server.modules.assistant.models import AssistantConversation, ChatUpload
from alloy_server.shared.exceptions import ConflictError, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.integrations.storage.uploads import UploadStorage
    from alloy_server.modules.assistant.uploads.schemas import ChatUploadCreate
    from alloy_server.modules.workspaces.dependencies import Membership


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
    storage: UploadStorage,
    membership: Membership,
    conversation: AssistantConversation,
    body: ChatUploadCreate,
) -> ChatUpload:
    """Commits. The caller hands out the upload URL."""
    storage.check_size(body.size)
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
    session: AsyncSession, storage: UploadStorage, membership: Membership, upload_id: UUID
) -> ChatUpload:
    """Called after the `PUT`. `ConflictError` when the object is not in the store
    yet; `PayloadTooLargeError`, and the object removed, when it is bigger than
    allowed. Repeating it is harmless. Commits."""
    upload = await get_upload(session, membership, upload_id)
    if upload.uploaded_at is None:
        info = await storage.verify(upload.key)
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
