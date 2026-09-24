from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from alloy_server.modules.assistant.models import AssistantConversation, AssistantMessage
from alloy_server.modules.assistant.uploads.service import purge_unattached
from alloy_server.shared.exceptions import NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.modules.workspaces.dependencies import Membership


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
