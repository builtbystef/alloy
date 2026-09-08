import logging
from contextlib import AbstractContextManager
from contextvars import Token
from typing import TYPE_CHECKING, Any

import logfire
from opentelemetry import context, propagate, trace
from opentelemetry.context import Context
from opentelemetry.trace import Span, SpanKind, StatusCode
from taskiq import TaskiqMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine
    from starlette.requests import Request
    from starlette.websockets import WebSocket
    from taskiq import TaskiqMessage, TaskiqResult

    from alloy_api.config import Settings


def enabled(settings: Settings) -> bool:
    return settings.logfire_token is not None


def configure(settings: Settings, *, service_name: str) -> logfire.LogfireLoggingHandler | None:
    """Connect to Logfire and return the handler that forwards the app's logs, or
    None when telemetry is off. Call once per process, before instrumenting."""
    if settings.logfire_token is None:
        return None
    logfire.configure(
        token=settings.logfire_token.get_secret_value(),
        service_name=service_name,
        environment=settings.logfire_environment,
        # The plain logging handler already prints to the terminal.
        console=False,
        # Do not continue a trace from an incoming `traceparent` header: the web
        # app sends none, and anyone could.
        distributed_tracing=False,
    )
    handler = logfire.LogfireLoggingHandler()
    handler.addFilter(_OwnLogsAndWarnings())
    return handler


class _OwnLogsAndWarnings(logging.Filter):
    """The app's own records at any level; libraries only when something is wrong.
    Keeps Taskiq's and Uvicorn's per-request chatter out."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("alloy_api") or record.levelno >= logging.WARNING


def quiet() -> AbstractContextManager[None]:
    """Records nothing inside. For polled checks, which would otherwise leave a
    span per poll."""
    return logfire.suppress_instrumentation()


def instrument_app(app: FastAPI) -> None:
    """One span per request. Health checks are polled, so they are left out (their
    handlers run under `quiet` for the same reason)."""
    logfire.instrument_fastapi(
        app,
        excluded_urls=r"/health(/.*)?$",
        request_attributes_mapper=_drop_endpoint_arguments,
    )


def instrument_engine(engine: AsyncEngine) -> None:
    """One span per SQL statement, under the request or job that ran it."""
    logfire.instrument_sqlalchemy(engine=engine.sync_engine)


def _drop_endpoint_arguments(
    _request: Request | WebSocket, attributes: dict[str, Any]
) -> dict[str, Any]:
    """The parsed endpoint arguments include emails, names, and passwords. Keep only
    which fields failed validation, which names no values."""
    return {"errors": attributes["errors"]} if attributes.get("errors") else {}


class TracingMiddleware(TaskiqMiddleware):
    """One span per job run, linked to the request that queued it.

    The trace context travels in the message labels, as Taskiq has no
    OpenTelemetry support of its own. Add it to the broker in every process
    that sends or runs jobs.
    """

    def __init__(self) -> None:
        super().__init__()
        self._runs: dict[str, tuple[Span, Token[Context]]] = {}

    def pre_send(self, message: TaskiqMessage) -> TaskiqMessage:
        propagate.inject(message.labels)
        return message

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        parent = propagate.extract(message.labels)
        span = trace.get_tracer(__name__).start_span(
            f"job {message.task_name}",
            context=parent,
            kind=SpanKind.CONSUMER,
            attributes={"job.name": message.task_name, "job.id": message.task_id},
        )
        token = context.attach(trace.set_span_in_context(span))
        self._runs[message.task_id] = (span, token)
        return message

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult[Any]) -> None:
        run = self._runs.pop(message.task_id, None)
        if run is None:
            return
        span, token = run
        if result.is_err:
            span.set_status(StatusCode.ERROR)
            if result.error is not None:
                span.record_exception(result.error)
        context.detach(token)
        span.end()
