import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from procrastinate import PsycopgConnector, RetryStrategy
from procrastinate.schema import SchemaManager
from sqlalchemy import text

from alloy_server.config import Settings
from alloy_server.db.base import utcnow
from alloy_server.integrations.mail import Email
from alloy_server.jobs import TASK_MODULES, conninfo, create_app
from alloy_server.jobs.app import RETRY_ON_ERROR, AnyTask, app, defer
from alloy_server.jobs.emails import queue_email, send_email
from alloy_server.jobs.imports import run_import_job
from alloy_server.jobs.purge import PurgeReport, purge, purge_expired
from alloy_server.jobs.stalled import retry_stalled
from alloy_server.modules.crm.imports.models import Import, ImportStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from tests.conftest import Actor, Database, InlineConnector, Outbox

    from alloy_server.integrations.storage.memory import MemoryObjectStore

    Join = Callable[[Actor, str, str], Actor]


async def run_now(db: Database, task: AnyTask) -> int:
    """Defer `task` from a session on the test transaction; the inline worker runs it."""
    async with db.session() as session:
        return await defer(session, task)


def test_the_app_queues_through_the_database():
    settings = Settings(database_url="postgresql+psycopg://u:p@db:5432/alloy")
    assert conninfo(settings) == "postgresql://u:p@db:5432/alloy"
    created = create_app(settings)
    assert isinstance(created.connector, PsycopgConnector)
    assert created.import_paths == TASK_MODULES
    assert created.worker_defaults == {"delete_jobs": "successful"}


def test_tasks_are_registered_with_their_retries_and_schedules():
    assert app.tasks["mail.send"] is send_email
    assert send_email.retry_strategy is RETRY_ON_ERROR
    assert isinstance(RETRY_ON_ERROR, RetryStrategy)
    assert RETRY_ON_ERROR.max_attempts == 5
    assert app.tasks["imports.run"] is run_import_job
    assert run_import_job.retry_strategy is None
    periodic = {name: task.cron for (name, _), task in app.periodic_registry.periodic_tasks.items()}
    assert periodic == {"purge.expired": "0 * * * *", "jobs.retry_stalled": "*/10 * * * *"}
    assert app.tasks["purge.expired"] is purge_expired
    assert app.tasks["jobs.retry_stalled"] is retry_stalled


def test_a_queued_email_goes_through_the_queue_to_the_mailer(
    db: Database, outbox: Outbox, queue: InlineConnector
):
    """The message is stored as JSON on the way, so what the mailer gets is a copy."""
    email = Email(to="grace@example.com", subject="Hi", text="Body", html="<p>Body</p>")

    async def queue_it() -> int:
        async with db.session() as session:
            return await queue_email(session, email)

    job_id = db.run(queue_it)
    assert outbox == [email]
    assert outbox[0] is not email
    stored = queue.jobs[job_id]
    assert stored["task_name"] == "mail.send"
    assert stored["args"]["email"] == {
        "to": "grace@example.com",
        "subject": "Hi",
        "text": "Body",
        "html": "<p>Body</p>",
    }


def test_a_job_is_queued_in_the_transaction_of_the_rows_it_is_about(
    db: Database, settings: Settings
):
    """Through the real connector (the in-memory one ignores the connection): the
    job row goes on the session's own connection, so it is rolled back, or
    committed, with the rest. The queue's tables are created in the test
    transaction and go with it."""
    real = create_app(settings)

    @real.task(name="tests.transactional")
    async def noop() -> None:
        pass

    async def scenario() -> tuple[int, int, list[int]]:
        if await db.connection.scalar(text("SELECT to_regclass('procrastinate_jobs')")) is None:
            await db.connection.exec_driver_sql(SchemaManager.get_schema().replace("%", "%%"))
        async with db.session() as session:
            rolled_back = await defer(session, noop)
            await session.rollback()
        async with db.session() as session:
            committed = await defer(session, noop)
            await session.commit()
        rows = await db.connection.scalars(
            text("SELECT id FROM procrastinate_jobs WHERE task_name = 'tests.transactional'")
        )
        return rolled_back, committed, list(rows)

    rolled_back, committed, rows = db.run(scenario)
    assert rolled_back != committed
    assert rows == [committed]


def test_retry_stalled_requeues_the_jobs_of_a_dead_worker(db: Database, queue: InlineConnector):
    """A job left running by a worker whose heartbeat stopped goes back to the
    queue (and, here, is run at once by the same worker); one held by a live
    worker is left alone."""
    dead, live = 1, 2
    long_ago = utcnow() - timedelta(minutes=5)
    queue.workers = {dead: long_ago, live: utcnow()}
    for job_id, worker_id in ((10, dead), (11, live)):
        queue.jobs[job_id] = {
            "id": job_id,
            "status": "doing",
            "task_name": "jobs.retry_stalled",
            "priority": 0,
            "lock": None,
            "queueing_lock": None,
            "args": {},
            "scheduled_at": None,
            "queue_name": "default",
            "attempts": 1,
            "worker_id": worker_id,
            "abort_requested": False,
        }
        queue.events[job_id] = [{"type": "started", "at": long_ago}]

    assert db.run(run_now, db, retry_stalled) > 0
    assert [e["type"] for e in queue.events[10]] == [
        "started",
        "scheduled",
        "deferred_for_retry",
        "started",
        "succeeded",
    ]
    assert queue.jobs[10]["status"] == "succeeded"
    assert queue.jobs[11]["status"] == "doing"


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
        "/auth/signup",
        json={"email": "dan@example.com", "password": "correct horse battery", "name": "Dan"},
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


def test_the_purge_task_runs_with_the_worker_resources_and_drops_old_failed_jobs(
    db: Database, queue: InlineConnector, caplog: pytest.LogCaptureFixture
):
    failed_long_ago = {
        "id": 10,
        "status": "failed",
        "task_name": "mail.send",
        "priority": 0,
        "lock": None,
        "queueing_lock": None,
        "args": {},
        "scheduled_at": None,
        "queue_name": "default",
        "attempts": 5,
        "worker_id": None,
        "abort_requested": False,
    }
    queue.jobs[10] = failed_long_ago
    queue.events[10] = [{"type": "failed", "at": utcnow() - timedelta(days=30)}]
    with caplog.at_level(logging.INFO, logger="alloy_server.jobs.purge"):
        db.run(run_now, db, purge_expired)
    assert "Purged PurgeReport(sessions=0, invites=0" in caplog.text
    assert 10 not in queue.jobs


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
        "/auth/signup",
        json={"email": "carol@example.com", "password": "correct horse battery", "name": "Carol"},
    )
    assert signup.status_code == 201
    report = db.run(run, later)
    assert (report.accounts, report.workspaces) == (0, 0)
