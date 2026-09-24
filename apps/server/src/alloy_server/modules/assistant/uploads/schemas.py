from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from alloy_server.modules.assistant.schemas import ResponseModel
from alloy_server.modules.crm.attachments.schemas import AttachmentCreate


class ChatUploadCreate(AttachmentCreate):
    """What the browser knows before uploading a file into the chat."""


class ChatUploadResponse(ResponseModel):
    id: UUID
    conversation_id: UUID
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime | None
    attachment_id: UUID | None
    created_at: datetime


class ChatUploadTicket(BaseModel):
    """Step one of a chat upload: `PUT` the file to `upload_url` with the
    `Content-Type` and `size` given at creation, then `POST .../uploads/{id}/complete`."""

    upload: ChatUploadResponse
    upload_url: str
    expires_at: datetime
