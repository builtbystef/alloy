import logging
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import UIMessage

from alloy_server.config import SettingsDep
from alloy_server.db.session import SessionDep
from alloy_server.integrations.rate_limit import Limit, RateLimiterDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.modules.assistant import service
from alloy_server.modules.assistant.agent import (
    USAGE_LIMITS,
    agent,
    history_capability,
    run_settings,
)
from alloy_server.modules.assistant.dependencies import AgentDeps, ModelDep
from alloy_server.modules.assistant.history import append_messages, load_history
from alloy_server.modules.assistant.models import AssistantConversation
from alloy_server.modules.assistant.schemas import (
    ChatMessageRequest,
    ConversationDetailResponse,
    ConversationResponse,
)
from alloy_server.modules.assistant.turn import (
    SDK_VERSION,
    ConversationAdapter,
    parse_time_zone,
    persist_run,
    prepare_turn,
)
from alloy_server.modules.assistant.uploads.router import router as uploads_router
from alloy_server.modules.workspaces.dependencies import CanReadCrm
from alloy_server.shared.logs import request_id

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRunResult
    from pydantic_ai.ui.vercel_ai.response_types import BaseChunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/assistant", tags=["assistant"])
router.include_router(uploads_router)

# Each message to the assistant is a model run; this bounds what one user can spend.
ASSISTANT_MESSAGE_PER_USER = Limit("assistant-message:user", 60, timedelta(hours=1))


def read_conversation(conversation: AssistantConversation) -> ConversationResponse:
    return ConversationResponse.model_validate(conversation)


@router.get("/conversations")
async def list_conversations(
    session: SessionDep, membership: CanReadCrm
) -> list[ConversationResponse]:
    """The caller's conversations in this workspace, most recently active first."""
    rows = await session.scalars(service.conversations_query(membership))
    return [read_conversation(c) for c in rows]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(session: SessionDep, membership: CanReadCrm) -> ConversationResponse:
    """A new, empty conversation. An existing one with no messages is returned
    instead, so "New chat" pressed twice does not pile up empty rows."""
    return read_conversation(await service.create_conversation(session, membership))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID, session: SessionDep, membership: CanReadCrm
) -> ConversationDetailResponse:
    """The conversation with its transcript as `UIMessage`s. A tool call still
    waiting for approval comes back in the `approval-requested` state."""
    conversation = await service.get_conversation(session, membership, conversation_id)
    history = await load_history(session, conversation.id)
    messages = _merge_assistant_turns(
        VercelAIAdapter.dump_messages(history, sdk_version=SDK_VERSION)
    )
    return ConversationDetailResponse(
        **read_conversation(conversation).model_dump(),
        messages=[m.model_dump(by_alias=True, exclude_none=True) for m in messages],
    )


def _merge_assistant_turns(messages: list[UIMessage]) -> list[UIMessage]:
    """One assistant message per reply, as the stream showed it. `dump_messages`
    makes one per model response, so a reply with tool calls would otherwise come
    back as several bubbles after a reload."""
    merged: list[UIMessage] = []
    for message in messages:
        previous = merged[-1] if merged else None
        if previous is not None and previous.role == "assistant" and message.role == "assistant":
            previous.parts = [*previous.parts, *message.parts]
            previous.id = message.id
            if isinstance(message.metadata, dict):
                base = previous.metadata if isinstance(previous.metadata, dict) else {}
                previous.metadata = {**base, **message.metadata}
        else:
            merged.append(message)
    return merged


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID, session: SessionDep, store: ObjectStoreDep, membership: CanReadCrm
) -> Response:
    """Removes the transcript and the chat's files that were never attached to a
    record. Attachments made from the chat stay on their records."""
    conversation = await service.get_conversation(session, membership, conversation_id)
    await service.delete_conversation(session, store, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def send_message(  # noqa: PLR0913, PLR0917
    conversation_id: UUID,
    body: ChatMessageRequest,
    request: Request,
    session: SessionDep,
    store: ObjectStoreDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    membership: CanReadCrm,
    model: ModelDep,
) -> Response:
    """Send a message, retry the last reply, or answer an approval request, and
    stream the assistant's reply as server-sent events (the Vercel AI data-stream
    protocol; `useChat` reads it).

    The body is what `useChat` sends. Only its last message is used: a `user`
    message is the new turn (files go as `upload_ids` in its `metadata`), an
    `assistant` message carries approval responses. `trigger: regenerate-message`
    repeats the last user turn. 503 when no model is configured, 429 past the
    per-user limit.
    """
    await limiter.hit(ASSISTANT_MESSAGE_PER_USER, str(membership.user.id))
    conversation = await service.get_conversation(session, membership, conversation_id)
    body.id = body.id or str(conversation.id)
    try:
        run_input = VercelAIAdapter.build_run_input(body.model_dump_json(by_alias=True).encode())
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, exc.errors(include_url=False)
        ) from exc

    deps = AgentDeps(
        session=session,
        membership=membership,
        store=store,
        settings=settings,
        request_id=request_id.get(),
        conversation_id=conversation.id,
        time_zone=parse_time_zone(body.tz),
    )
    adapter = ConversationAdapter(
        agent=agent,
        run_input=run_input,
        accept=request.headers.get("accept"),
        sdk_version=SDK_VERSION,
    )
    adapter.prompt = await prepare_turn(deps, conversation, adapter)

    history = await load_history(session, conversation.id)
    if adapter.prompt is not None:
        # Stored before the run, so a failed run still shows what the user said.
        await append_messages(session, conversation, [adapter.prompt])
    await session.commit()

    async def on_complete(result: AgentRunResult[Any]) -> AsyncIterator[BaseChunk]:
        await persist_run(deps, conversation, result)
        return
        yield  # pragma: no cover - makes this an async generator

    stream = adapter.run_stream(
        message_history=history,
        conversation_id=str(conversation.id),
        model=model,
        deps=deps,
        model_settings=run_settings(settings, deps),
        usage_limits=USAGE_LIMITS,
        capabilities=[history_capability],
        on_complete=on_complete,
    )
    return adapter.streaming_response(stream)
