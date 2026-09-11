from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from alloy_api.crm.schemas import AttachmentCreate


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ConversationRead(ReadModel):
    id: UUID
    title: str | None = Field(description="Null until the first message names it.")
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[dict[str, Any]] = Field(
        description="The transcript as Vercel AI SDK `UIMessage`s, for `useChat`."
    )


class ChatMessageRequest(BaseModel):
    """What `useChat` posts: the chat id, the trigger, and the messages the browser
    has. Only the last message is read; the server holds the history. `tz` is the
    user's IANA time zone."""

    id: str | None = None
    trigger: str = "submit-message"
    messages: list[dict[str, Any]]
    tz: str | None = None
    message_id: str | None = Field(None, alias="messageId")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ChatUploadCreate(AttachmentCreate):
    """What the browser knows before uploading a file into the chat."""


class ChatUploadRead(ReadModel):
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

    upload: ChatUploadRead
    upload_url: str
    expires_at: datetime
