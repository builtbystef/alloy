"""The job runner: which broker `Settings` picks, that a queued email is sent, and
what the purge job removes. Jobs run inline on the in-memory broker with the
test transaction (see conftest), so a handler's side effects are visible at once.
"""

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from taskiq import InMemoryBroker, SmartRetryMiddleware, TaskiqScheduler
from taskiq_redis import ListRedisScheduleSource, RedisAsyncResultBackend, RedisStreamBroker

from alloy_api.config import Settings
from alloy_api.crm.models import Import, ImportStatus
from alloy_api.jobs import create_broker, create_scheduler, ping_redis
from alloy_api.jobs.context import RequestIdMiddleware
from alloy_api.jobs.emails import send_email
from alloy_api.jobs.purge import PurgeReport, purge, purge_expired
from alloy_api.mail import Email
from alloy_api.models import utcnow

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from tests.conftest import Actor, Database, Outbox

    from alloy_api.storage.memory import MemoryObjectStore

    Join = Callable[[Actor, str, str], Actor]


@pytest.fixture
def settings() -> Settings:
    """This module's app talks to the real Redis, so `/health/redis` is exercised."""
    return Settings(app_name="Test API", jobs_broker="redis")


def test_redis_settings_build_a_stream_broker_with_retries_and_a_scheduler():
    settings = Settings(app_name="Test API", jobs_broker="redis")
    broker = create_broker(settings)
    assert isinstance(broker, RedisStreamBroker)
    assert isinstance(broker.result_backend, RedisAsyncResultBackend)
    retry, request_ids = broker.middlewares
    assert isinstance(retry, SmartRetryMiddleware)
    assert isinstance(retry.schedule_source, ListRedisScheduleSource)
    assert isinstance(request_ids, RequestIdMiddleware)

    scheduler = create_scheduler(broker, settings)
    assert isinstance(scheduler, TaskiqScheduler)
    assert len(scheduler.sources) == 2  # cron labels, plus the delayed retries


def test_memory_settings_build_an_in_memory_broker():
    settings = Settings(app_name="Test API", jobs_broker="memory")
    broker = create_broker(settings)
    assert isinstance(broker, InMemoryBroker)
    (request_ids,) = broker.middlewares
    assert isinstance(request_ids, RequestIdMiddleware)
    assert len(create_scheduler(broker, settings).sources) == 1


def test_tasks_are_registered_with_their_labels():
    assert send_email.task_name == "mail.send"
    assert send_email.labels["retry_on_error"] is True
    assert purge_expired.task_name == "purge.expired"
    assert purge_expired.labels["schedule"] == [{"cron": "0 * * * *"}]


def test_health_redis_pings_the_server(client: TestClient):
    response = client.get("/health/redis")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}


def test_ping_redis_reports_an_unreachable_server():
    with pytest.raises(RedisConnectionError):
        asyncio.run(ping_redis("redis://127.0.0.1:1/0"))


def test_a_queued_email_goes_through_the_broker_to_the_mailer(db: Database, outbox: Outbox):
    """The message is serialized on the way, so what the mailer gets is a copy."""
    email = Email(to="grace@example.com", subject="Hi", text="Body", html="<p>Body</p>")

    async def send() -> None:
        task = await send_email.kiq(email)
        result = await task.wait_result(timeout=5)
        assert result.is_err is False, result.error

    db.run(send)
    assert outbox == [email]
    assert outbox[0] is not email


def test_purge_removes_only_what_has_been_dead_long_enough(  # noqa: PLR0913, PLR0917
    client: TestClient,
    alice: Actor,
    join: Join,
    outbox: Outbox,
    db: Database,
    object_store: MemoryObjectStore,
    settings: Settings,
):
    # A revoked login: a second session for Alice, logged out again.
    login = client.post(
        "/auth/login", json={"email": alice.email, "password": "correct horse battery"}
    )
    assert login.status_code == 200
    assert client.post("/auth/logout").status_code == 204
    # An accepted invitation.
    join(alice, "grace@example.com", "member")
    # An account that never followed its verification link.
    signup = client.post(
        "/auth/signup", json={"email": "dan@example.com", "password": "correct horse battery"}
    )
    assert signup.status_code == 201
    client.cookies.clear()
    verification = outbox[-1].text.split("/verify-email?token=")[1].split()[0]
    # A password reset link that was never followed.
    assert client.post("/auth/forgot-password", json={"email": alice.email}).status_code == 204
    reset = outbox[-1].text.split("/reset-password?token=")[1].split()[0]
    # An attachment and an import whose files were never uploaded, plus one
    # attachment whose file did land but was never reported complete.
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    ticket = alice.post(
        f"/contacts/{contact['id']}/attachments",
        json={"filename": "a.pdf", "content_type": "application/pdf", "size": 1},
    ).json()
    alice.post(
        f"/contacts/{contact['id']}/attachments",
        json={"filename": "b.pdf", "content_type": "application/pdf", "size": 1},
    )
    object_store.objects[object_store.key_of(ticket["upload_url"])] = (b"x", "application/pdf")
    alice.post("/imports/", json={"kind": "contacts", "filename": "c.csv", "size": 1})

    async def run(now) -> PurgeReport:
        async with db.session() as session:
            return await purge(session, object_store, settings, now=now)

    # Nothing is old enough yet.
    assert db.run(run, utcnow()) == PurgeReport()

    later = utcnow() + settings.purge_after + settings.verification_ttl + timedelta(hours=1)
    assert db.run(run, later) == PurgeReport(
        sessions=1,
        invites=1,
        verification_tokens=1,
        password_reset_tokens=1,
        attachments=2,
        imports=1,
    )
    assert object_store.objects == {}
    # The spent link is gone, not merely expired.
    assert client.post("/auth/verify-email", json={"token": verification}).status_code == 404
    reset_body = {"token": reset, "new_password": "new horse battery"}
    assert client.post("/auth/reset-password", json=reset_body).status_code == 404
    # Live logins and completed rows are untouched.
    assert alice.get("/members").status_code == 200
    assert [c["name"] for c in alice.get("/contacts/").json()["items"]] == ["Grace"]
    assert db.run(run, later) == PurgeReport()


def test_purge_fails_imports_stuck_in_queued_or_running(
    alice: Actor, db: Database, object_store: MemoryObjectStore, settings: Settings
):
    """A job that was never delivered, or died in a way the broker will not
    redeliver, must not show as running forever."""
    ticket = alice.post(
        "/imports/", json={"kind": "contacts", "filename": "c.csv", "size": 1}
    ).json()
    import_id = ticket["import"]["id"]
    key = object_store.key_of(ticket["upload_url"])
    object_store.objects[key] = (b"name\nGrace\n", "text/csv")

    async def mark(status: ImportStatus) -> None:
        async with db.session() as session:
            record = await session.get_one(Import, UUID(import_id))
            record.status = status
            await session.commit()

    async def run(now) -> PurgeReport:
        async with db.session() as session:
            return await purge(session, object_store, settings, now=now)

    db.run(mark, ImportStatus.QUEUED)
    assert db.run(run, utcnow()) == PurgeReport()
    assert alice.get(f"/imports/{import_id}").json()["status"] == "queued"

    later = utcnow() + settings.import_timeout + timedelta(minutes=1)
    assert db.run(run, later) == PurgeReport(timed_out_imports=1)
    failed = alice.get(f"/imports/{import_id}").json()
    assert failed["status"] == "failed"
    assert "did not finish" in failed["error"]
    assert failed["finished_at"] is not None
    assert key not in object_store.objects
    assert db.run(run, later) == PurgeReport()


def test_the_purge_task_runs_with_the_worker_resources(db: Database):
    async def run() -> dict[str, int]:
        task = await purge_expired.kiq()
        result = await task.wait_result(timeout=5)
        assert result.is_err is False, result.error
        return result.return_value

    assert db.run(run) == {
        "sessions": 0,
        "invites": 0,
        "verification_tokens": 0,
        "password_reset_tokens": 0,
        "email_change_tokens": 0,
        "attachments": 0,
        "chat_uploads": 0,
        "imports": 0,
        "timed_out_imports": 0,
        "accounts": 0,
        "workspaces": 0,
    }


def test_purge_removes_deleted_accounts_and_the_workspaces_they_were_alone_in(  # noqa: PLR0913, PLR0917
    client: TestClient,
    alice: Actor,
    join: Join,
    outbox: Outbox,
    db: Database,
    object_store: MemoryObjectStore,
    settings: Settings,
):
    # Carol is alone in her own workspace and a member of Alice's.
    carol = join(alice, "carol@example.com", "member")
    own = client.get("/workspaces/", headers=carol.headers).json()
    own_id = next(w["id"] for w in own if w["id"] != alice.workspace)
    contact = client.post(
        f"/workspaces/{own_id}/contacts/", json={"name": "Dan"}, headers=carol.headers
    ).json()
    ticket = client.post(
        f"/workspaces/{own_id}/contacts/{contact['id']}/attachments",
        json={"filename": "a.pdf", "content_type": "application/pdf", "size": 1},
        headers=carol.headers,
    ).json()
    key = object_store.key_of(ticket["upload_url"])
    object_store.objects[key] = (b"x", "application/pdf")
    assert (
        client.post(
            f"/workspaces/{own_id}/attachments/{ticket['attachment']['id']}/complete",
            headers=carol.headers,
        ).status_code
        == 200
    )
    body = {"new_email": "caroline@example.com", "current_password": "correct horse battery"}
    assert client.post("/auth/change-email", json=body, headers=carol.headers).status_code == 204
    change = outbox[-1].text.split("/confirm-email?token=")[1].split()[0]

    response = client.post(
        "/auth/delete-account",
        json={"current_password": "correct horse battery"},
        headers=carol.headers,
    )
    assert response.status_code == 204, response.text

    async def run(now) -> PurgeReport:
        async with db.session() as session:
            return await purge(session, object_store, settings, now=now)

    report = db.run(run, utcnow())
    assert (report.accounts, report.workspaces) == (0, 0)
    assert client.post("/auth/confirm-email", json={"token": change}).status_code == 404

    later = utcnow() + settings.account_deletion_grace + timedelta(hours=1)
    report = db.run(run, later)
    assert (report.accounts, report.workspaces) == (1, 1)
    assert key not in object_store.objects
    assert [m["email"] for m in alice.get("/members").json()] == [alice.email]
    assert client.get("/workspaces/", headers=alice.headers).status_code == 200
    login = client.post(
        "/auth/login", json={"email": "carol@example.com", "password": "correct horse battery"}
    )
    assert login.status_code == 401
    signup = client.post(
        "/auth/signup", json={"email": "carol@example.com", "password": "correct horse battery"}
    )
    assert signup.status_code == 201
    report = db.run(run, later)
    assert (report.accounts, report.workspaces) == (0, 0)
