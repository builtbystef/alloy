from uuid import UUID

from fastapi import APIRouter, status

from alloy_server.db.base import utcnow
from alloy_server.db.session import SessionDep
from alloy_server.modules.agent import service
from alloy_server.modules.agent.schemas import (
    ChatUploadCreate,
    ChatUploadResponse,
    ChatUploadTicket,
)
from alloy_server.modules.crm.attachments.dependencies import AttachmentStorageDep
from alloy_server.modules.workspaces.dependencies import CanReadCrm

router = APIRouter(tags=["agent"])


@router.post("/conversations/{conversation_id}/uploads", status_code=status.HTTP_201_CREATED)
async def create_upload(
    conversation_id: UUID,
    body: ChatUploadCreate,
    session: SessionDep,
    storage: AttachmentStorageDep,
    membership: CanReadCrm,
) -> ChatUploadTicket:
    """Start a chat upload: the row is created and an upload URL returned. Same size
    limit as attachments; 413 above it."""
    conversation = await service.get_conversation(session, membership, conversation_id)
    upload = await service.start_upload(session, storage, membership, conversation, body)
    return ChatUploadTicket(
        upload=ChatUploadResponse.model_validate(upload),
        upload_url=await storage.store.upload_url(
            upload.key, upload.content_type, upload.size, storage.settings.storage_url_ttl
        ),
        expires_at=utcnow() + storage.settings.storage_url_ttl,
    )


@router.post("/uploads/{upload_id}/complete")
async def complete_upload(
    upload_id: UUID, session: SessionDep, storage: AttachmentStorageDep, membership: CanReadCrm
) -> ChatUploadResponse:
    """Called after the `PUT`. 409 when the object is not in the store yet; 413, and
    the object removed, when it is bigger than allowed. Repeating it is harmless."""
    upload = await service.complete_upload(session, storage, membership, upload_id)
    return ChatUploadResponse.model_validate(upload)


@router.delete("/uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: UUID, session: SessionDep, storage: AttachmentStorageDep, membership: CanReadCrm
) -> None:
    """Discard a chat upload the user removed before sending: the row and the
    object. 409 once it has become an attachment, which owns the object then."""
    await service.delete_upload(session, storage.store, membership, upload_id)
