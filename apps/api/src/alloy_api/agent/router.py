import logging
from collections.abc import AsyncIterator
from dataclasses import KW_ONLY, dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserContent,
    UserPromptPart,
)
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import FileUIPart, TextUIPart, UIMessage
from sqlalchemy import exists, select

from alloy_api.agent import uploads
from alloy_api.agent.agent import (
    USAGE_LIMITS,
    agent,
    build_model,
    history_capability,
    model_settings,
)
from alloy_api.agent.deps import AgentDeps
from alloy_api.agent.history import append_messages, load_history, truncate_after_last_prompt
from alloy_api.agent.models import AgentConversation, AgentMessage, ChatUpload
from alloy_api.agent.schemas import ChatMessageRequest, ConversationDetail, ConversationRead
from alloy_api.agent.uploads import fetch_conversation, purge_unattached
from alloy_api.config import SettingsDep
from alloy_api.db import SessionDep
from alloy_api.logs import request_id
from alloy_api.ratelimit import AGENT_MESSAGE_PER_USER, LimiterDep
from alloy_api.storage import ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.run import AgentRunResult
    from pydantic_ai.ui.vercel_ai.response_types import BaseChunk
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.storage import ObjectStore
    from alloy_api.workspaces.deps import Membership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/agent", tags=["agent"])
router.include_router(uploads.router)

SDK_VERSION = 7
TITLE_LENGTH = 80
# Files the model can read. Anything else is described by name, type, and size.
READABLE_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}
)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


def get_agent_model(settings: SettingsDep) -> Model:
    """The configured model; 503 when no key is set. Tests override it with a
    scripted model."""
    model = build_model(settings)
    if model is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The assistant is not configured: set ALLOY_OPENAI_API_KEY",
        )
    return model


AgentModelDep = Annotated["Model", Depends(get_agent_model)]


def read_conversation(conversation: AgentConversation) -> ConversationRead:
    return ConversationRead.model_validate(conversation)


@router.get("/conversations")
async def list_conversations(session: SessionDep, membership: CanReadCrm) -> list[ConversationRead]:
    """The caller's conversations in this workspace, most recently active first."""
    rows = await session.scalars(
        select(AgentConversation)
        .where(AgentConversation.workspace_id == membership.workspace.id)
        .where(AgentConversation.user_id == membership.user.id)
        .order_by(AgentConversation.updated_at.desc(), AgentConversation.id.desc())
    )
    return [read_conversation(c) for c in rows]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(session: SessionDep, membership: CanReadCrm) -> ConversationRead:
    """A new, empty conversation. An existing one with no messages is returned
    instead, so "New chat" pressed twice does not pile up empty rows."""
    has_messages = exists().where(AgentMessage.conversation_id == AgentConversation.id)
    empty = await session.scalar(
        select(AgentConversation)
        .where(AgentConversation.workspace_id == membership.workspace.id)
        .where(AgentConversation.user_id == membership.user.id)
        .where(~has_messages)
        .order_by(AgentConversation.created_at.desc())
        .limit(1)
    )
    if empty is not None:
        return read_conversation(empty)
    conversation = AgentConversation(
        workspace_id=membership.workspace.id, user_id=membership.user.id
    )
    session.add(conversation)
    await session.commit()
    return read_conversation(conversation)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID, session: SessionDep, membership: CanReadCrm
) -> ConversationDetail:
    """The conversation with its transcript as `UIMessage`s. A tool call still
    waiting for approval comes back in the `approval-requested` state."""
    conversation = await fetch_conversation(session, membership, conversation_id)
    history = await load_history(session, conversation.id)
    messages = _merge_assistant_turns(
        VercelAIAdapter.dump_messages(history, sdk_version=SDK_VERSION)
    )
    return ConversationDetail(
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
    conversation = await fetch_conversation(session, membership, conversation_id)
    await purge_unattached(session, store, conversation)
    await session.delete(conversation)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Sending a message -------------------------------------------------------------


def _time_zone(name: str | None) -> ZoneInfo:
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError, ValueError:
        return ZoneInfo("UTC")


def _title_from(text: str) -> str | None:
    line = " ".join(text.split())
    if not line:
        return None
    return line if len(line) <= TITLE_LENGTH else line[: TITLE_LENGTH - 1] + "…"


async def _uploads_for(
    session: AsyncSession, membership: Membership, conversation: AgentConversation, ids: list[Any]
) -> list[ChatUpload]:
    """The uploads named in a message's metadata: this user's, in this conversation,
    and complete. Anything else is a 400, not silently dropped."""
    if not ids:
        return []
    try:
        wanted = [UUID(str(i)) for i in ids]
    except ValueError as exc:
        raise bad_request("Bad upload id") from exc
    rows = {
        u.id: u
        for u in await session.scalars(
            select(ChatUpload)
            .where(ChatUpload.id.in_(wanted))
            .where(ChatUpload.conversation_id == conversation.id)
            .where(ChatUpload.user_id == membership.user.id)
        )
    }
    result = []
    for upload_id in wanted:
        upload = rows.get(upload_id)
        if upload is None:
            raise bad_request(f"Unknown upload {upload_id}")
        if upload.uploaded_at is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{upload.filename} has not finished uploading"
            )
        result.append(upload)
    return result


async def _file_content(
    store: ObjectStore, upload: ChatUpload, max_bytes: int
) -> BinaryContent | None:
    """The bytes for the model, when the file is a kind it can read and small enough."""
    if upload.content_type not in READABLE_TYPES or upload.size > max_bytes:
        return None
    data = await store.get(upload.key)
    return BinaryContent(data, media_type=upload.content_type, identifier=upload.filename)


async def _build_prompt(
    deps: AgentDeps, conversation: AgentConversation, message: UIMessage
) -> ModelRequest:
    """The user's turn: their text, the files they sent (readable ones as content,
    the rest by name), and a line listing every file with its upload id."""
    text = "\n".join(part.text for part in message.parts if isinstance(part, TextUIPart)).strip()
    if any(isinstance(part, FileUIPart) for part in message.parts):
        raise bad_request("Send files as upload ids in the message metadata")
    metadata = message.metadata if isinstance(message.metadata, dict) else {}
    upload_rows = await _uploads_for(
        deps.session, deps.membership, conversation, list(metadata.get("upload_ids") or [])
    )
    content: list[UserContent] = [text] if text else []
    for upload in upload_rows:
        binary = await _file_content(deps.store, upload, deps.settings.agent_file_read_max_bytes)
        if binary is not None:
            content.append(binary)
    if upload_rows:
        listing = "; ".join(
            f"{u.filename} ({u.content_type}, {u.size} bytes, upload_id {u.id})"
            for u in upload_rows
        )
        content.append(f"[Files sent with this message: {listing}]")
    if not content:
        raise bad_request("The message is empty")
    prompt: str | list[UserContent] = content
    if len(content) == 1 and isinstance(content[0], str):
        prompt = content[0]
    stored_metadata = {
        "uploads": [
            {
                "id": str(u.id),
                "filename": u.filename,
                "content_type": u.content_type,
                "size": u.size,
            }
            for u in upload_rows
        ]
    }
    return ModelRequest(
        parts=[UserPromptPart(content=prompt)],
        metadata=stored_metadata if upload_rows else None,
    )


@dataclass
class ConversationAdapter(VercelAIAdapter[AgentDeps, Any]):
    """The Vercel adapter with the browser's message list ignored.

    The server holds the history, so the only thing taken from the request is the
    newest turn: a user message becomes `prompt`, built by the route with its files;
    an assistant message carries approval responses, which the base class reads.
    """

    _: KW_ONLY
    prompt: ModelRequest | None = None

    @cached_property
    def messages(self) -> list[ModelMessage]:
        return [self.prompt] if self.prompt is not None else []


async def _prepare_turn(
    deps: AgentDeps, conversation: AgentConversation, adapter: ConversationAdapter
) -> ModelRequest | None:
    """The user's new turn as a request, or None when the request only answers an
    approval. A retry repeats the last stored user turn."""
    run_input = adapter.run_input
    last = run_input.messages[-1] if run_input.messages else None
    if run_input.trigger == "regenerate-message":
        prompt = await truncate_after_last_prompt(deps.session, conversation)
        if prompt is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Nothing to retry yet")
        return ModelRequest(parts=prompt.parts, metadata=prompt.metadata)
    if last is not None and last.role == "user":
        if conversation.title is None:
            text = "\n".join(p.text for p in last.parts if isinstance(p, TextUIPart))
            conversation.title = _title_from(text) or "Files"
        return await _build_prompt(deps, conversation, last)
    if adapter.deferred_tool_results is None:
        raise bad_request("Send a user message or an approval response")
    return None


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
    limiter: LimiterDep,
    membership: CanReadCrm,
    model: AgentModelDep,
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
    await limiter.hit(AGENT_MESSAGE_PER_USER, str(membership.user.id))
    conversation = await fetch_conversation(session, membership, conversation_id)
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
        time_zone=_time_zone(body.tz),
    )
    adapter = ConversationAdapter(
        agent=agent,
        run_input=run_input,
        accept=request.headers.get("accept"),
        sdk_version=SDK_VERSION,
    )
    adapter.prompt = await _prepare_turn(deps, conversation, adapter)

    history = await load_history(session, conversation.id)
    if adapter.prompt is not None:
        # Stored before the run, so a failed run still shows what the user said.
        await append_messages(session, conversation, [adapter.prompt])
    await session.commit()

    async def on_complete(result: AgentRunResult[Any]) -> AsyncIterator[BaseChunk]:
        new_messages = result.new_messages()
        if deps.approval_previews:
            for message in reversed(new_messages):
                if isinstance(message, ModelResponse):
                    message.metadata = {
                        **(message.metadata or {}),
                        "approval_previews": deps.approval_previews,
                    }
                    break
        await append_messages(session, conversation, new_messages)
        await session.commit()
        return
        yield  # pragma: no cover - makes this an async generator

    stream = adapter.run_stream(
        message_history=history,
        conversation_id=str(conversation.id),
        model=model,
        deps=deps,
        model_settings=model_settings(settings, deps),
        usage_limits=USAGE_LIMITS,
        capabilities=[history_capability],
        on_complete=on_complete,
    )
    return adapter.streaming_response(stream)
