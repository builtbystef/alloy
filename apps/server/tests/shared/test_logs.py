import json
import logging
from typing import TYPE_CHECKING

import pytest

from alloy_server.jobs.app import defer, task
from alloy_server.jobs.resources import Resources
from alloy_server.shared.logs import JsonFormatter, RequestIdFilter, TextFormatter, request_id

if TYPE_CHECKING:
    from types import TracebackType

    from fastapi.testclient import TestClient
    from tests.conftest import Database

    ExcInfo = tuple[type[BaseException], BaseException, TracebackType | None]

log = logging.getLogger("alloy_server.tests")


def record(message: str, exc_info: ExcInfo | None = None) -> logging.LogRecord:
    rec = logging.LogRecord("alloy_server.tests", logging.INFO, __file__, 1, message, (), exc_info)
    RequestIdFilter().filter(rec)
    return rec


def test_text_lines_carry_a_utc_timestamp_and_the_request_id():
    token = request_id.set("report-1")
    try:
        line = TextFormatter().format(record("hello"))
    finally:
        request_id.reset(token)
    timestamp, rest = line.split(" ", 1)
    assert timestamp.endswith("Z")
    assert "T" in timestamp
    assert rest == "INFO [alloy_server.tests] [report-1] hello"


def test_json_lines_are_one_object_each():
    exc = ValueError("nope")
    rec = record("it broke", exc_info=(type(exc), exc, None))
    line = json.loads(JsonFormatter().format(rec))
    assert line["level"] == "INFO"
    assert line["logger"] == "alloy_server.tests"
    assert line["request_id"] == "-"
    assert line["message"] == "it broke"
    assert line["time"].endswith("Z")
    assert "ValueError: nope" in line["exception"]
    assert "\n" not in JsonFormatter().format(record("one\nline"))


seen: list[str] = []


@task("tests.log_request_id")
async def log_request_id(_res: Resources) -> None:
    log.info("inside the job")
    seen.append(request_id.get())


async def run_job(db: Database) -> str:
    async with db.session() as session:
        await defer(session, log_request_id)
    return seen.pop()


def test_a_job_runs_under_the_request_id_that_queued_it(
    client: TestClient, db: Database, caplog: pytest.LogCaptureFixture
):
    """Jobs run as soon as they are deferred (see conftest), so the queueing
    context is a plain `request_id.set`, as the API's middleware does it."""

    async def queue_inside_request() -> str:
        token = request_id.set("report-9")
        try:
            return await run_job(db)
        finally:
            request_id.reset(token)

    caplog.handler.addFilter(RequestIdFilter())
    assert client.portal is not None
    with caplog.at_level(logging.INFO, logger="alloy_server.tests"):
        assert client.portal.call(queue_inside_request) == "report-9"
    (inside,) = [r for r in caplog.records if r.getMessage() == "inside the job"]
    assert getattr(inside, "request_id", None) == "report-9"


def test_a_job_queued_outside_a_request_gets_its_own_id(client: TestClient, db: Database):
    assert client.portal is not None
    rid = client.portal.call(run_job, db)
    assert rid != "-"
    assert len(rid) == 16
    assert client.portal.call(run_job, db) != rid
    assert request_id.get() == "-"
