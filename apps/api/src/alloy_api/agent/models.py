import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_api.models import Base, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from alloy_api.crm.models import Attachment


class AgentConversation(UUIDPrimaryKey, Timestamps, Base):
    """One chat between a user and the assistant, inside one workspace. The server
    owns the transcript: `messages` is what the model sees, in order."""

    __tablename__ = "agent_conversations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Null until the first message, which names the conversation.
    title: Mapped[str | None] = mapped_column(String(120))

    messages: Mapped[list["AgentMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AgentMessage.position",
    )


class AgentMessage(UUIDPrimaryKey, Base):
    """One Pydantic AI `ModelMessage` (a request or a response), serialized with
    `ModelMessagesTypeAdapter`, at `position` in its conversation."""

    __tablename__ = "agent_messages"
    __table_args__ = (UniqueConstraint("conversation_id", "position"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[AgentConversation] = relationship(back_populates="messages")


class ChatUpload(UUIDPrimaryKey, Base):
    """A file dropped into the chat. Uploaded like an attachment (row first, then a
    presigned PUT, then `complete`), under `workspaces/{ws}/chat-uploads/{id}`.

    `attachment_id` is set once a tool turns it into an attachment on a contact or
    company; the attachment points at the same object, so no bytes are copied. An
    upload never attached is purged after `chat_upload_ttl`, row and object together.
    """

    __tablename__ = "chat_uploads"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger)
    key: Mapped[str] = mapped_column(String(512), unique=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    attachment: Mapped["Attachment | None"] = relationship()
