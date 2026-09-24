"""One turn of a conversation: the user's new message (with the files it names) as
a model request, and the run's result written back to the transcript."""

from dataclasses import KW_ONLY, dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
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
from sqlalchemy import select

from alloy_server.integrations.ai.usage import record_model_calls
from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.history import append_messages, truncate_after_last_prompt
from alloy_server.modules.assistant.models import AssistantConversation, ChatUpload

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRunResult
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.modules.workspaces.dependencies import Membership

# The Vercel AI SDK message format the browser speaks.
SDK_VERSION = 7
TITLE_LENGTH = 80
# Files the model can read. Anything else is described by name, type, and size.
READABLE_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}
)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


def parse_time_zone(name: str | None) -> ZoneInfo:
    """The user's IANA zone, or UTC when it is missing or unknown."""
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError, ValueError:
        return ZoneInfo("UTC")


def title_from(text: str) -> str | None:
    line = " ".join(text.split())
    if not line:
        return None
    return line if len(line) <= TITLE_LENGTH else line[: TITLE_LENGTH - 1] + "…"


# --- The user's message ------------------------------------------------------------


async def _uploads_for(
    session: AsyncSession,
    membership: Membership,
    conversation: AssistantConversation,
    ids: list[Any],
) -> list[ChatUpload]:
    """The uploads named in a message's metadata: this user's, in this conversation,
    and complete. Anything else is a 400, not silently dropped."""
    if not ids:
        return []
    try:
        wanted = [UUID(str(i)) for i in ids]
    except ValueError as exc:
        raise _bad_request("Bad upload id") from exc
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
            raise _bad_request(f"Unknown upload {upload_id}")
        if upload.uploaded_at is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{upload.filename} has not finished uploading"
            )
        result.append(upload)
    return result


async def _file_content(
    store: ObjectStore, upload: ChatUpload, max_bytes: int
) -> BinaryContent | None:
    if upload.content_type not in READABLE_TYPES or upload.size > max_bytes:
        return None
    data = await store.get(upload.key)
    return BinaryContent(data, media_type=upload.content_type, identifier=upload.filename)


async def build_prompt(
    deps: AgentDeps, conversation: AssistantConversation, message: UIMessage
) -> ModelRequest:
    """The user's turn: their text, the files they sent (readable ones as content,
    the rest by name), and a line listing every file with its upload id."""
    text = "\n".join(part.text for part in message.parts if isinstance(part, TextUIPart)).strip()
    if any(isinstance(part, FileUIPart) for part in message.parts):
        raise _bad_request("Send files as upload ids in the message metadata")
    metadata = message.metadata if isinstance(message.metadata, dict) else {}
    upload_rows = await _uploads_for(
        deps.session, deps.membership, conversation, list(metadata.get("upload_ids") or [])
    )
    content: list[UserContent] = [text] if text else []
    for upload in upload_rows:
        binary = await _file_content(
            deps.store, upload, deps.settings.assistant_file_read_max_bytes
        )
        if binary is not None:
            content.append(binary)
    if upload_rows:
        listing = "; ".join(
            f"{u.filename} ({u.content_type}, {u.size} bytes, upload_id {u.id})"
            for u in upload_rows
        )
        content.append(f"[Files sent with this message: {listing}]")
    if not content:
        raise _bad_request("The message is empty")
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


async def prepare_turn(
    deps: AgentDeps, conversation: AssistantConversation, adapter: ConversationAdapter
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
            conversation.title = title_from(text) or "Files"
        return await build_prompt(deps, conversation, last)
    if adapter.deferred_tool_results is None:
        raise _bad_request("Send a user message or an approval response")
    return None


# --- The assistant's reply ---------------------------------------------------------


async def persist_run(
    deps: AgentDeps, conversation: AssistantConversation, result: AgentRunResult[Any]
) -> None:
    """Store the run's new messages, with any approval previews on the response that
    paused, and record its model calls. Commits."""
    new_messages = result.new_messages()
    if deps.approval_previews:
        for message in reversed(new_messages):
            if isinstance(message, ModelResponse):
                message.metadata = {
                    **(message.metadata or {}),
                    "approval_previews": deps.approval_previews,
                }
                break
    await append_messages(deps.session, conversation, new_messages)
    record_model_calls(
        deps.session,
        new_messages,
        workspace_id=deps.workspace_id,
        user_id=deps.membership.user.id,
        source="assistant",
        request_id=deps.request_id,
    )
    await deps.session.commit()
