from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(ResponseModel):
    id: UUID
    title: str | None = Field(description="Null until the first message names it.")
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
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
