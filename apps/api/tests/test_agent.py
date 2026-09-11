"""The assistant: conversations, the streaming message endpoint, tool behaviour, the
approval round-trip, chat uploads, and the purge of stale uploads.

The model is a scripted `FunctionModel`: each test lists the turns it wants the
model to take (a tool call or a text reply), so no network is involved. Tools run
for real against the rolled-back test transaction.
"""

import asyncio
import json
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.agent import tools
from alloy_api.agent.agent import HISTORY_TURNS, trim_history
from alloy_api.agent.deps import AgentDeps
from alloy_api.agent.models import AgentMessage, ChatUpload
from alloy_api.agent.router import get_agent_model
from alloy_api.config import Settings
from alloy_api.crm.models import Attachment
from alloy_api.jobs.purge import PurgeReport, purge
from alloy_api.main import app
from alloy_api.models import utcnow
from alloy_api.ratelimit import AGENT_MESSAGE_PER_USER, Limiter, MemoryRateLimitStore
from alloy_api.workspaces.deps import Membership
from alloy_api.workspaces.models import WorkspaceMember

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from tests.conftest import Actor, Database

    from alloy_api.storage.memory import MemoryObjectStore

    Join = Callable[[Actor, str, str], Actor]


# --- A scripted model --------------------------------------------------------------


class Script:
    """The model's turns, consumed one per request. A `str` is a text reply; a
    `(tool_name, args)` pair is a tool call. `seen_tools` records what tools the
    model was offered on each request."""

    def __init__(self, *turns: str | tuple[str, dict[str, Any]]) -> None:
        self.turns = list(turns)
        self.seen_tools: list[list[str]] = []
        self.prompts: list[list[ModelMessage]] = []
        self.calls = 0

    def model(self) -> FunctionModel:
        async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[Any]:
            self.seen_tools.append(sorted(t.name for t in info.function_tools))
            self.prompts.append(messages)
            if not self.turns:
                yield "I have nothing more to say."
                return
            turn = self.turns.pop(0)
            self.calls += 1
            if isinstance(turn, str):
                yield turn
            else:
                name, args = turn
                yield {
                    0: DeltaToolCall(
                        name=name, json_args=json.dumps(args), tool_call_id=f"call_{self.calls}"
                    )
                }

        return FunctionModel(stream_function=stream)


@pytest.fixture
def script() -> Script:
    return Script()


@pytest.fixture(autouse=True)
def scripted_model(script: Script) -> None:
    app.dependency_overrides[get_agent_model] = script.model


def events(text: str) -> list[dict[str, Any]]:
    """The chunks of a data-stream response, in order."""
    return [
        json.loads(line[6:])
        for line in text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


def of_type(chunks: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [c for c in chunks if c["type"] == kind]


def reply_text(chunks: list[dict[str, Any]]) -> str:
    return "".join(c["delta"] for c in of_type(chunks, "text-delta"))


def user_message(text: str, **metadata: Any) -> dict[str, Any]:
    message: dict[str, Any] = {
        "id": "m1",
        "role": "user",
        "parts": [{"type": "text", "text": text}],
    }
    if metadata:
        message["metadata"] = metadata
    return message


def approval_response(chunks: list[dict[str, Any]], *, approved: bool, reason: str | None = None):
    """The assistant message `useChat` sends back after Approve or Deny."""
    parts = []
    for request in of_type(chunks, "tool-approval-request"):
        call = next(
            c
            for c in of_type(chunks, "tool-input-available")
            if c["toolCallId"] == request["toolCallId"]
        )
        approval: dict[str, Any] = {"id": request["approvalId"], "approved": approved}
        if reason:
            approval["reason"] = reason
        parts.append(
            {
                "type": f"tool-{call['toolName']}",
                "toolCallId": call["toolCallId"],
                "state": "approval-responded",
                "input": call["input"],
                "approval": approval,
            }
        )
    return {"id": "a1", "role": "assistant", "parts": parts}


def upload(actor: Actor, store: MemoryObjectStore, path: str, body: dict, data: bytes) -> dict:
    """An ordinary attachment upload on a record, as in test_attachments."""
    ticket = actor.post(path, json=body).json()
    store.objects[store.key_of(ticket["upload_url"])] = (data, body["content_type"])
    completed = actor.post(f"/attachments/{ticket['attachment']['id']}/complete")
    assert completed.status_code == 200, completed.text
    return completed.json()


class Chat:
    """One conversation, driven the way the browser drives it."""

    def __init__(self, actor: Actor) -> None:
        self.actor = actor
        created = actor.post("/agent/conversations")
        assert created.status_code == 201, created.text
        self.id = created.json()["id"]

    def path(self, suffix: str = "") -> str:
        return f"/agent/conversations/{self.id}{suffix}"

    def send(self, text: str, **metadata: Any) -> list[dict[str, Any]]:
        return self.post([user_message(text, **metadata)])

    def post(self, messages: list[dict[str, Any]], **extra: Any) -> list[dict[str, Any]]:
        response = self.actor.post(
            self.path("/messages"),
            json={"id": self.id, "messages": messages, "tz": "Europe/Belgrade", **extra},
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        return events(response.text)

    def detail(self) -> dict[str, Any]:
        response = self.actor.get(self.path())
        assert response.status_code == 200, response.text
        return response.json()


# --- Conversations -----------------------------------------------------------------


def test_conversations_belong_to_one_user_in_one_workspace(alice: Actor, bob: Actor, join: Join):
    chat = Chat(alice)
    assert [c["id"] for c in alice.get("/agent/conversations").json()] == [chat.id]
    assert chat.detail() == {
        "id": chat.id,
        "title": None,
        "created_at": chat.detail()["created_at"],
        "updated_at": chat.detail()["updated_at"],
        "messages": [],
    }
    # Another user in the same workspace does not see it; nor does another workspace.
    carol = join(alice, "carol@example.com", "member")
    assert carol.get("/agent/conversations").json() == []
    assert carol.get(chat.path()).status_code == 404
    assert bob.get(f"/agent/conversations/{chat.id}").status_code == 404
    assert bob.delete(f"/agent/conversations/{chat.id}").status_code == 404
    assert alice.delete(chat.path()).status_code == 204
    assert alice.get(chat.path()).status_code == 404


def test_new_chat_reuses_an_empty_conversation(alice: Actor, script: Script):
    first = Chat(alice)
    assert Chat(alice).id == first.id
    script.turns.append("Hello!")
    first.send("hi")
    assert Chat(alice).id != first.id


def test_viewers_can_chat(alice: Actor, join: Join, script: Script):
    viewer = join(alice, "vera@example.com", "viewer")
    script.turns.append("Sure.")
    chat = Chat(viewer)
    assert reply_text(chat.send("hello")) == "Sure."


def test_unconfigured_assistant_answers_503(alice: Actor):
    app.dependency_overrides.pop(get_agent_model)
    chat = Chat(alice)
    response = alice.post(
        chat.path("/messages"), json={"id": chat.id, "messages": [user_message("hi")]}
    )
    assert response.status_code == 503
    assert "ALLOY_OPENAI_API_KEY" in response.json()["detail"]


def test_messages_are_rate_limited_per_user(alice: Actor, rate_limits: MemoryRateLimitStore):
    chat = Chat(alice)
    me = alice.client.get("/auth/me", headers=alice.headers).json()
    key = Limiter.key(AGENT_MESSAGE_PER_USER, me["id"])

    async def fill() -> None:
        for _ in range(AGENT_MESSAGE_PER_USER.limit):
            await rate_limits.hit(key, AGENT_MESSAGE_PER_USER.window)

    asyncio.run(fill())
    response = alice.post(
        chat.path("/messages"), json={"id": chat.id, "messages": [user_message("hi")]}
    )
    assert response.status_code == 429
    assert response.headers["retry-after"]


# --- Reads, single writes, and the transcript --------------------------------------


def test_a_read_tool_answers_from_the_workspace(alice: Actor, script: Script):
    alice.post("/companies/", json={"name": "Acme"})
    grace = alice.post(
        "/contacts/", json={"name": "Grace Hopper", "email": "grace@example.com"}
    ).json()
    script.turns += [("search_contacts", {"q": "grace"}), "Grace Hopper is at grace@example.com."]
    chat = Chat(alice)
    chunks = chat.send("Who is Grace?")

    (call,) = of_type(chunks, "tool-input-available")
    assert call["toolName"] == "search_contacts"
    (output,) = of_type(chunks, "tool-output-available")
    assert [row["id"] for row in output["output"]["items"]] == [grace["id"]]
    assert output["output"]["items"][0]["url"].endswith(
        f"/{alice.workspace}/contacts/{grace['id']}"
    )
    assert reply_text(chunks) == "Grace Hopper is at grace@example.com."
    # The model saw the date and the workspace in its instructions.
    request = script.prompts[0][-1]
    assert isinstance(request, ModelRequest)
    instructions = request.instructions or ""
    assert "Europe/Belgrade" in instructions
    assert alice.email in instructions

    # The transcript is stored and comes back as UI messages, titled by the first prompt.
    detail = chat.detail()
    assert detail["title"] == "Who is Grace?"
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    tool_part = next(p for p in detail["messages"][1]["parts"] if p["type"].startswith("tool-"))
    assert tool_part["state"] == "output-available"
    assert [c["title"] for c in alice.get("/agent/conversations").json()] == ["Who is Grace?"]


def test_a_single_create_runs_at_once_and_is_marked(alice: Actor, script: Script):
    alice.post("/companies/", json={"name": "Acme"})
    script.turns += [
        (
            "create_contacts",
            {"items": [{"name": "Jane Doe", "email": "jane@example.com", "company_name": "Acme"}]},
        ),
        "Added Jane Doe at Acme.",
    ]
    chunks = Chat(alice).send("Add Jane from Acme as a contact")
    assert of_type(chunks, "tool-approval-request") == []
    (output,) = of_type(chunks, "tool-output-available")
    (created,) = output["output"]["created"]
    assert created["company"] == "Acme"

    contact = alice.get(f"/contacts/{created['id']}").json()
    assert contact["name"] == "Jane Doe"
    assert contact["company"]["name"] == "Acme"
    assert contact["created_by"]["email"] == alice.email
    assert contact["source"] == "agent"


def test_a_duplicate_email_is_flagged_not_created(alice: Actor, script: Script):
    existing = alice.post("/contacts/", json={"name": "Jane", "email": "jane@example.com"}).json()
    script.turns += [
        ("create_contacts", {"items": [{"name": "Jane Doe", "email": "jane@example.com"}]}),
        "There is already a Jane with that email.",
    ]
    chunks = Chat(alice).send("Add Jane")
    (output,) = of_type(chunks, "tool-output-available")
    assert output["output"]["created"] == []
    assert output["output"]["skipped"][0]["existing"]["id"] == existing["id"]
    assert alice.get("/contacts/").json()["total"] == 1


def test_an_unknown_company_name_asks_the_model_to_correct(alice: Actor, script: Script):
    script.turns += [
        ("create_contacts", {"items": [{"name": "Jane Doe", "company_name": "Nowhere Inc"}]}),
        "I could not find that company.",
    ]
    chunks = Chat(alice).send("Add Jane from Nowhere Inc")
    (error,) = of_type(chunks, "tool-output-error")
    assert "No company named 'Nowhere Inc'" in error["errorText"]
    assert alice.get("/contacts/").json()["total"] == 0


def test_logging_a_call_marks_the_contact_as_contacted(alice: Actor, script: Script):
    grace = alice.post("/contacts/", json={"name": "Grace"}).json()
    script.turns += [
        (
            "log_activities",
            {"items": [{"contact_id": grace["id"], "type": "call", "notes": "Intro"}]},
        ),
        "Logged.",
    ]
    Chat(alice).send("Log a call with Grace")
    assert alice.get(f"/contacts/{grace['id']}").json()["last_contacted_at"] is not None
    (activity,) = alice.get(f"/contacts/{grace['id']}/activities").json()["items"]
    assert activity["type"] == "call"
    assert activity["source"] == "agent"


def test_regenerate_repeats_the_last_turn(alice: Actor, script: Script):
    script.turns += ["First answer.", "Second answer."]
    chat = Chat(alice)
    chat.send("hello")
    chunks = chat.post([user_message("hello")], trigger="regenerate-message", messageId="x")
    assert reply_text(chunks) == "Second answer."
    detail = chat.detail()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["parts"][0]["text"] == "Second answer."


# --- Approval ----------------------------------------------------------------------


def test_a_bulk_create_pauses_until_approved(alice: Actor, script: Script):
    items = [{"name": "Ann"}, {"name": "Ben"}, {"name": "Cy"}]
    script.turns += [("create_contacts", {"items": items}), "Created Ann, Ben, and Cy."]
    chat = Chat(alice)
    chunks = chat.send("Add Ann, Ben, and Cy")

    (request,) = of_type(chunks, "tool-approval-request")
    (preview,) = of_type(chunks, "data-approval_preview")
    assert preview["data"]["title"] == "Create 3 contacts"
    assert preview["data"]["columns"] == ["Name", "Email", "Company"]
    assert [row[0] for row in preview["data"]["rows"]] == ["Ann", "Ben", "Cy"]
    assert preview["data"]["tool_call_id"] == request["toolCallId"]
    assert of_type(chunks, "text-delta") == []
    assert alice.get("/contacts/").json()["total"] == 0

    # After a reload the pending call is still waiting, with its preview.
    detail = chat.detail()
    tool_part = next(p for p in detail["messages"][-1]["parts"] if p["type"].startswith("tool-"))
    assert tool_part["state"] == "approval-requested"
    assert (
        detail["messages"][-1]["metadata"]["approval_previews"][request["toolCallId"]]["total"] == 3
    )

    resumed = chat.post([approval_response(chunks, approved=True)])
    (output,) = of_type(resumed, "tool-output-available")
    assert [c["name"] for c in output["output"]["created"]] == ["Ann", "Ben", "Cy"]
    assert reply_text(resumed) == "Created Ann, Ben, and Cy."
    assert alice.get("/contacts/").json()["total"] == 3
    assert [m["role"] for m in chat.detail()["messages"]] == ["user", "assistant"]


def test_a_denied_delete_changes_nothing(alice: Actor, script: Script):
    grace = alice.post("/contacts/", json={"name": "Grace", "email": "g@example.com"}).json()
    script.turns += [("delete_contacts", {"contact_ids": [grace["id"]]}), "Left it alone."]
    chat = Chat(alice)
    chunks = chat.send("Delete Grace")
    (preview,) = of_type(chunks, "data-approval_preview")
    assert preview["data"]["title"] == "Delete 1 contact"
    assert preview["data"]["rows"] == [["Grace", "g@example.com", ""]]

    resumed = chat.post([approval_response(chunks, approved=False, reason="Changed my mind")])
    assert of_type(resumed, "tool-output-denied")
    assert reply_text(resumed) == "Left it alone."
    assert alice.get(f"/contacts/{grace['id']}").status_code == 200
    # The denial is part of the stored transcript.
    tool_part = next(
        p for p in chat.detail()["messages"][-1]["parts"] if p["type"].startswith("tool-")
    )
    assert tool_part["state"] == "output-denied"


def test_an_approved_delete_removes_the_rows(
    alice: Actor, script: Script, object_store: MemoryObjectStore
):
    grace = alice.post("/contacts/", json={"name": "Grace"}).json()
    upload(alice, object_store, f"/contacts/{grace['id']}/attachments", PDF, b"hello world")
    script.turns += [("delete_contacts", {"contact_ids": [grace["id"]]}), "Deleted Grace."]
    chat = Chat(alice)
    chunks = chat.send("Delete Grace")
    resumed = chat.post([approval_response(chunks, approved=True)])
    assert of_type(resumed, "tool-output-available")[0]["output"] == {"deleted": ["Grace"]}
    assert alice.get(f"/contacts/{grace['id']}").status_code == 404
    assert object_store.objects == {}


def test_bulk_calls_are_capped(alice: Actor, script: Script):
    items = [{"name": f"Person {i}"} for i in range(tools.MAX_BULK + 1)]
    script.turns += [("create_contacts", {"items": items}), "Too many."]
    chunks = Chat(alice).send("Add everyone")
    (error,) = of_type(chunks, "tool-output-error")
    assert f"At most {tools.MAX_BULK} items" in error["errorText"]
    assert alice.get("/contacts/").json()["total"] == 0


# --- Permissions and isolation -----------------------------------------------------


def test_viewers_are_offered_read_tools_only_and_cannot_write(
    alice: Actor, join: Join, script: Script
):
    viewer = join(alice, "vera@example.com", "viewer")
    script.turns += [("create_contacts", {"items": [{"name": "Jane"}]}), "I cannot do that."]
    chunks = Chat(viewer).send("Add Jane")
    assert all(
        not name.startswith(("create_", "update_", "delete_", "log_", "attach_"))
        for name in script.seen_tools[0]
    )
    assert "search_contacts" in script.seen_tools[0]
    assert of_type(chunks, "tool-output-available") == []
    assert alice.get("/contacts/").json()["total"] == 0


def test_members_are_offered_every_tool(alice: Actor, script: Script):
    script.turns.append("Hi.")
    Chat(alice).send("hi")
    assert len(script.seen_tools[0]) == 21
    assert set(tools.WRITE_TOOL_NAMES) < set(script.seen_tools[0])


def test_tools_cannot_reach_another_workspace(alice: Actor, bob: Actor, script: Script):
    theirs = bob.post("/contacts/", json={"name": "Bob's contact"}).json()
    script.turns += [("get_contact", {"contact_id": theirs["id"]}), "No such contact."]
    chunks = Chat(alice).send("Show me that contact")
    (error,) = of_type(chunks, "tool-output-error")
    assert "in this workspace" in error["errorText"]


# --- Files in the chat -------------------------------------------------------------


PDF = {"filename": "card.pdf", "content_type": "application/pdf", "size": 11}


def chat_upload(chat: Chat, store: MemoryObjectStore, body: dict, data: bytes) -> dict:
    """Start, PUT, and complete a chat upload the way the browser does."""
    started = chat.actor.post(chat.path("/uploads"), json=body)
    assert started.status_code == 201, started.text
    ticket = started.json()
    assert ticket["upload"]["uploaded_at"] is None
    key = store.key_of(ticket["upload_url"])
    assert key == f"workspaces/{chat.actor.workspace}/chat-uploads/{ticket['upload']['id']}"
    store.objects[key] = (data, body["content_type"])
    completed = chat.actor.post(f"/agent/uploads/{ticket['upload']['id']}/complete")
    assert completed.status_code == 200, completed.text
    return completed.json()


def test_upload_lifecycle_start_complete_attach(
    alice: Actor, script: Script, object_store: MemoryObjectStore
):
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    chat = Chat(alice)
    uploaded = chat_upload(chat, object_store, PDF, b"hello world")
    assert uploaded["uploaded_at"] is not None
    assert uploaded["attachment_id"] is None

    script.turns += [
        ("attach_files", {"items": [{"upload_id": uploaded["id"], "company_id": acme["id"]}]}),
        "Attached card.pdf to Acme.",
    ]
    chunks = chat.send("Attach this to Acme", upload_ids=[uploaded["id"]])
    # A small PDF is shown to the model; the listing names it with its upload id.
    prompt = script.prompts[0][-1]
    assert isinstance(prompt, ModelRequest)
    (part,) = prompt.parts
    assert isinstance(part, UserPromptPart)
    assert isinstance(part.content[1], BinaryContent)
    assert part.content[1].media_type == "application/pdf"
    assert uploaded["id"] in str(part.content[2])

    (output,) = of_type(chunks, "tool-output-available")
    (attachment,) = output["output"]
    assert attachment["filename"] == "card.pdf"
    assert attachment["company_id"] == acme["id"]
    listed = alice.get(f"/companies/{acme['id']}/attachments").json()["items"]
    assert [a["id"] for a in listed] == [attachment["id"]]
    assert listed[0]["uploaded_by"]["email"] == alice.email
    # The same object, not a copy; the download works through the normal route.
    assert len(object_store.objects) == 1
    download = alice.get(f"/attachments/{attachment['id']}/download", follow_redirects=False)
    assert download.status_code == 307

    # The stored transcript names the file but does not keep its bytes.
    stored = chat.detail()["messages"][0]
    assert stored["metadata"]["uploads"][0]["filename"] == "card.pdf"
    assert "was shown here" in json.dumps(stored["parts"])
    assert "aGVsbG8" not in json.dumps(stored)  # no base64 of "hello"

    # Deleting the conversation keeps the attached file.
    assert alice.delete(chat.path()).status_code == 204
    assert len(object_store.objects) == 1


def test_uploads_belong_to_their_user_and_conversation(
    alice: Actor, join: Join, script: Script, object_store: MemoryObjectStore
):
    carol = join(alice, "carol@example.com", "member")
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    theirs = chat_upload(Chat(carol), object_store, PDF, b"hello world")

    alice_chat = Chat(alice)
    # Not sendable as a message attachment...
    response = alice.post(
        alice_chat.path("/messages"),
        json={
            "id": alice_chat.id,
            "messages": [user_message("Attach this", upload_ids=[theirs["id"]])],
        },
    )
    assert response.status_code == 400
    # ...and not attachable by the tool, even by id.
    script.turns += [
        ("attach_files", {"items": [{"upload_id": theirs["id"], "company_id": acme["id"]}]}),
        "That file is not in this conversation.",
    ]
    chunks = alice_chat.send("Attach that")
    (error,) = of_type(chunks, "tool-output-error")
    assert "No file with upload id" in error["errorText"]
    assert alice.get(f"/companies/{acme['id']}/attachments").json()["items"] == []
    # Nor can Alice complete Carol's upload.
    assert alice.post(f"/agent/uploads/{theirs['id']}/complete").status_code == 404


def test_an_incomplete_upload_is_refused(alice: Actor):
    chat = Chat(alice)
    ticket = alice.post(chat.path("/uploads"), json=PDF).json()
    assert alice.post(f"/agent/uploads/{ticket['upload']['id']}/complete").status_code == 409
    response = alice.post(
        chat.path("/messages"),
        json={"id": chat.id, "messages": [user_message("hi", upload_ids=[ticket["upload"]["id"]])]},
    )
    assert response.status_code == 409


@pytest.mark.parametrize("settings", [10], indirect=True)
def test_upload_size_limit(alice: Actor, object_store: MemoryObjectStore):
    chat = Chat(alice)
    assert alice.post(chat.path("/uploads"), json={**PDF, "size": 11}).status_code == 413
    ticket = alice.post(chat.path("/uploads"), json={**PDF, "size": 5}).json()
    key = object_store.key_of(ticket["upload_url"])
    object_store.objects[key] = (b"0123456789ab", "application/pdf")
    assert alice.post(f"/agent/uploads/{ticket['upload']['id']}/complete").status_code == 413
    assert key not in object_store.objects


@pytest.fixture
def settings(request: pytest.FixtureRequest) -> Settings:
    limit = getattr(request, "param", None)
    if limit is None:
        return Settings(app_name="Test API", openai_api_key=None)
    return Settings(app_name="Test API", openai_api_key=None, attachment_max_bytes=limit)


def test_removing_a_file_before_sending_deletes_its_upload(
    alice: Actor, join: Join, script: Script, object_store: MemoryObjectStore
):
    chat = Chat(alice)
    uploaded = chat_upload(chat, object_store, PDF, b"hello world")
    # Someone else cannot delete it.
    carol = join(alice, "carol@example.com", "member")
    assert carol.delete(f"/agent/uploads/{uploaded['id']}").status_code == 404
    assert alice.delete(f"/agent/uploads/{uploaded['id']}").status_code == 204
    assert object_store.objects == {}
    assert alice.delete(f"/agent/uploads/{uploaded['id']}").status_code == 404
    # Deleting only the row; an in-flight upload that was never completed also goes.
    ticket = alice.post(chat.path("/uploads"), json=PDF).json()
    assert alice.delete(f"/agent/uploads/{ticket['upload']['id']}").status_code == 204

    # Once attached, the attachment owns the object and the upload cannot be deleted.
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    attached = chat_upload(chat, object_store, PDF, b"hello world")
    script.turns += [
        ("attach_files", {"items": [{"upload_id": attached["id"], "company_id": acme["id"]}]}),
        "Done.",
    ]
    chat.send("Attach this", upload_ids=[attached["id"]])
    assert alice.delete(f"/agent/uploads/{attached['id']}").status_code == 409
    assert len(object_store.objects) == 1


def test_deleting_a_conversation_purges_its_unattached_uploads(
    alice: Actor, object_store: MemoryObjectStore
):
    chat = Chat(alice)
    chat_upload(chat, object_store, PDF, b"hello world")
    assert len(object_store.objects) == 1
    assert alice.delete(chat.path()).status_code == 204
    assert object_store.objects == {}


def test_purge_removes_stale_unattached_uploads(
    alice: Actor, db: Database, object_store: MemoryObjectStore, settings: Settings, script: Script
):
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    chat = Chat(alice)
    stale = chat_upload(chat, object_store, PDF, b"hello world")
    attached = chat_upload(chat, object_store, {**PDF, "filename": "kept.pdf"}, b"hello world")
    script.turns += [
        ("attach_files", {"items": [{"upload_id": attached["id"], "company_id": acme["id"]}]}),
        "Attached.",
    ]
    chat.send("Attach kept.pdf to Acme", upload_ids=[attached["id"]])

    async def run(now) -> PurgeReport:
        async with db.session() as session:
            return await purge(session, object_store, settings, now=now)

    assert db.run(run, utcnow()) == PurgeReport()
    later = utcnow() + settings.chat_upload_ttl + timedelta(minutes=1)
    assert db.run(run, later) == PurgeReport(chat_uploads=1)
    keys = set(object_store.objects)
    assert len(keys) == 1
    assert stale["id"] not in "".join(keys)
    assert attached["id"] in "".join(keys)


# --- Tools called directly ---------------------------------------------------------


async def tool_context(db: Database, actor: Actor, settings: Settings) -> RunContext[AgentDeps]:
    session = db.session()
    member = await session.scalar(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user), selectinload(WorkspaceMember.workspace))
        .where(WorkspaceMember.workspace_id == UUID(actor.workspace))
    )
    assert member is not None
    deps = AgentDeps(
        session=session,
        membership=Membership(workspace=member.workspace, member=member),
        store=None,  # ty: ignore[invalid-argument-type] - these tools do not touch storage
        settings=settings,
        request_id="test",
        conversation_id=UUID(int=0),
    )
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


def test_search_contacts_staleness_and_grouping(alice: Actor, db: Database, settings: Settings):
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    globex = alice.post("/companies/", json={"name": "Globex"}).json()
    recent = (utcnow() - timedelta(days=2)).isoformat()
    old = (utcnow() - timedelta(days=60)).isoformat()
    alice.post(
        "/contacts/", json={"name": "Fresh", "company_id": acme["id"], "last_contacted_at": recent}
    )
    alice.post(
        "/contacts/", json={"name": "Quiet", "company_id": acme["id"], "last_contacted_at": old}
    )
    alice.post("/contacts/", json={"name": "Silent", "company_id": globex["id"]})

    async def run():
        ctx = await tool_context(db, alice, settings)
        stale = await tools.search_contacts(ctx, stale_days=30)
        grouped = await tools.search_contacts(ctx, stale_days=30, group_by_company=True)
        companies = await tools.search_companies(ctx)
        return stale, grouped, companies

    stale, grouped, companies = db.run(run)
    assert isinstance(stale, tools.Page)
    assert [c.name for c in stale.items] == ["Silent", "Quiet"]  # never contacted first
    assert stale.next_page is None
    assert isinstance(grouped, tools.GroupedContacts)
    assert [
        (g.company.name if g.company else None, [c.name for c in g.contacts])
        for g in grouped.groups
    ] == [
        ("Globex", ["Silent"]),
        ("Acme", ["Quiet"]),
    ]
    by_name = {c.name: c for c in companies.items}
    assert by_name["Acme"].contact_count == 2
    assert by_name["Acme"].latest_contact_at is not None
    assert by_name["Globex"].contact_count == 1
    assert by_name["Globex"].latest_contact_at is None


def test_list_tasks_uses_the_callers_time_zone(alice: Actor, db: Database, settings: Settings):
    alice.post("/tasks/", json={"title": "Late", "due_at": "2020-01-01T09:00:00Z"})
    alice.post(
        "/tasks/", json={"title": "Done", "due_at": "2020-01-01T09:00:00Z", "status": "done"}
    )
    alice.post("/tasks/", json={"title": "Someday"})

    async def run():
        ctx = await tool_context(db, alice, settings)
        ctx.deps.time_zone = ZoneInfo("Pacific/Auckland")
        overdue = await tools.list_tasks(ctx, due="overdue")
        every = await tools.list_tasks(ctx, status=None)
        info = await tools.get_workspace(ctx)
        return overdue, every, info

    overdue, every, info = db.run(run)
    assert [t.title for t in overdue.items] == ["Late"]
    assert sorted(t.title for t in every.items) == ["Done", "Late", "Someday"]
    assert info.time_zone == "Pacific/Auckland"
    assert info.you_can_write is True


def test_get_contact_and_company_details(alice: Actor, db: Database, settings: Settings):
    acme = alice.post("/companies/", json={"name": "Acme", "notes": "Big"}).json()
    grace = alice.post("/contacts/", json={"name": "Grace", "company_id": acme["id"]}).json()
    alice.post(f"/contacts/{grace['id']}/activities", json={"type": "note", "notes": "Hi"})
    alice.post("/tasks/", json={"title": "Call back", "contact_id": grace["id"]})

    async def run():
        ctx = await tool_context(db, alice, settings)
        return await tools.get_contact(ctx, UUID(grace["id"])), await tools.get_company(
            ctx, UUID(acme["id"])
        )

    contact, company = db.run(run)
    assert contact.contact.company == "Acme"
    assert [a.type.value for a in contact.recent_activities] == ["note"]
    assert [t.title for t in contact.open_tasks] == ["Call back"]
    assert company.notes == "Big"
    assert [c.name for c in company.contacts] == ["Grace"]
    assert company.more_contacts == 0


def test_history_trimming_keeps_whole_turns():
    messages: list[ModelMessage] = []
    for i in range(HISTORY_TURNS + 5):
        messages.append(ModelRequest(parts=[UserPromptPart(content=f"q{i}")]))
        messages.append(ModelResponse(parts=[TextPart(content=f"a{i}")]))
    trimmed = trim_history(messages)
    assert len(trimmed) == 2 * HISTORY_TURNS + 1
    note, first_kept = trimmed[0], trimmed[1]
    assert isinstance(note, ModelRequest)
    assert isinstance(first_kept, ModelRequest)
    note_part, kept_part = note.parts[0], first_kept.parts[0]
    assert isinstance(note_part, UserPromptPart)
    assert isinstance(kept_part, UserPromptPart)
    assert "5 earlier turns" in str(note_part.content)
    assert kept_part.content == "q5"
    assert trim_history(messages[:4]) == messages[:4]


def test_messages_endpoint_validates_the_body(alice: Actor):
    chat = Chat(alice)
    assert alice.post(chat.path("/messages"), json={"messages": []}).status_code == 400
    assert (
        alice.post(
            chat.path("/messages"), json={"id": chat.id, "messages": [{"role": "user"}]}
        ).status_code
        == 422
    )
    empty = alice.post(
        chat.path("/messages"), json={"id": chat.id, "messages": [user_message("   ")]}
    )
    assert empty.status_code == 400
    # A conversation with no messages has nothing to retry.
    retry = alice.post(
        chat.path("/messages"),
        json={"id": chat.id, "trigger": "regenerate-message", "messages": []},
    )
    assert retry.status_code == 409


def test_the_chat_upload_rows_are_gone_with_their_workspace(
    alice: Actor, db: Database, object_store: MemoryObjectStore
):
    chat = Chat(alice)
    chat_upload(chat, object_store, PDF, b"hello world")
    assert alice.client.delete(alice.ws(), headers=alice.headers).status_code == 204

    async def count() -> int:
        async with db.session() as session:
            return len(list(await session.scalars(select(ChatUpload))))

    assert db.run(count) == 0
    assert object_store.objects == {}


def test_agent_messages_are_stored_in_order(alice: Actor, db: Database, script: Script):
    script.turns += ["One.", "Two."]
    chat = Chat(alice)
    chat.send("first")
    chat.send("second")

    async def positions() -> list[int]:
        async with db.session() as session:
            rows = await session.scalars(
                select(AgentMessage.position)
                .where(AgentMessage.conversation_id == UUID(chat.id))
                .order_by(AgentMessage.position)
            )
            return list(rows)

    assert db.run(positions) == [0, 1, 2, 3]
    assert [m["role"] for m in chat.detail()["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    # The second run saw the first exchange.
    assert len(script.prompts[1]) == 3


def test_attachment_rows_from_chat_are_normal_attachments(
    alice: Actor, db: Database, script: Script, object_store: MemoryObjectStore
):
    grace = alice.post("/contacts/", json={"name": "Grace"}).json()
    chat = Chat(alice)
    uploaded = chat_upload(chat, object_store, PDF, b"hello world")
    script.turns += [
        ("create_contacts", {"items": [{"name": "Jane", "upload_ids": [uploaded["id"]]}]}),
        "Done.",
    ]
    chat.send("Add Jane with this card", upload_ids=[uploaded["id"]])

    async def rows() -> tuple[Attachment, ChatUpload]:
        async with db.session() as session:
            attachment = await session.scalar(select(Attachment))
            upload_row = await session.scalar(select(ChatUpload))
            assert attachment is not None
            assert upload_row is not None
            return attachment, upload_row

    attachment, upload_row = db.run(rows)
    assert attachment.key == upload_row.key
    assert upload_row.attachment_id == attachment.id
    assert attachment.contact_id != UUID(grace["id"])
    jane = next(c for c in alice.get("/contacts/").json()["items"] if c["name"] == "Jane")
    assert attachment.contact_id == UUID(jane["id"])
    # Deleting the attachment through the UI route works as for any attachment.
    assert alice.delete(f"/attachments/{attachment.id}").status_code == 204
    assert object_store.objects == {}
