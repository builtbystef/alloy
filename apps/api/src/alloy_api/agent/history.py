from typing import TYPE_CHECKING, Any

from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    UserPromptPart,
)
from sqlalchemy import func, select

from alloy_api.agent.models import AgentConversation, AgentMessage
from alloy_api.models import utcnow

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


async def load_history(session: AsyncSession, conversation_id: Any) -> list[ModelMessage]:  # noqa: ANN401
    bodies = list(
        await session.scalars(
            select(AgentMessage.body)
            .where(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.position)
        )
    )
    return ModelMessagesTypeAdapter.validate_python(bodies) if bodies else []


def without_binary(message: ModelMessage) -> ModelMessage:
    """The message with file bytes replaced by a note, so the transcript stays small
    and a file is only ever sent to the model once."""
    if not isinstance(message, ModelRequest):
        return message
    parts = []
    for part in message.parts:
        if isinstance(part, UserPromptPart) and not isinstance(part.content, str):
            content: list[Any] = []
            for item in part.content:
                if isinstance(item, BinaryContent):
                    name = item.identifier or item.media_type
                    content.append(f"[The file {name} was shown here.]")
                else:
                    content.append(item)
            parts.append(UserPromptPart(content=content, timestamp=part.timestamp))
        else:
            parts.append(part)
    return ModelRequest(
        parts=parts,
        instructions=message.instructions,
        run_id=message.run_id,
        conversation_id=message.conversation_id,
        metadata=message.metadata,
        timestamp=message.timestamp,
    )


async def append_messages(
    session: AsyncSession, conversation: AgentConversation, messages: Sequence[ModelMessage]
) -> None:
    """Store `messages` after the conversation's last position. Flushed, not committed."""
    if not messages:
        return
    last = await session.scalar(
        select(func.max(AgentMessage.position)).where(
            AgentMessage.conversation_id == conversation.id
        )
    )
    position = (last if last is not None else -1) + 1
    bodies = ModelMessagesTypeAdapter.dump_python(
        [without_binary(m) for m in messages], mode="json"
    )
    now = utcnow()
    for offset, body in enumerate(bodies):
        session.add(
            AgentMessage(
                conversation_id=conversation.id,
                position=position + offset,
                body=body,
                created_at=now,
            )
        )
    conversation.updated_at = now
    await session.flush()


async def truncate_after_last_prompt(
    session: AsyncSession, conversation: AgentConversation
) -> ModelRequest | None:
    """For a retry: drop everything from the last user prompt on, and return that
    prompt so the run can be repeated. None when there is no prompt to repeat."""
    rows = list(
        await session.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation.id)
            .order_by(AgentMessage.position)
        )
    )
    messages = ModelMessagesTypeAdapter.validate_python([r.body for r in rows]) if rows else []
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, ModelRequest) and any(
            isinstance(part, UserPromptPart) for part in message.parts
        ):
            for row in rows[index:]:
                await session.delete(row)
            await session.flush()
            return message
    return None
