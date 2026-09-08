import logging
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="-")

FORMAT = "%(levelname)s [%(name)s] [%(request_id)s] %(message)s"


class RequestIdFilter(logging.Filter):
    """Adds `request_id` to every record, for `FORMAT`."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def configure(level: str) -> None:
    """A handler and level for the app's loggers (Uvicorn and Taskiq configure only
    their own). A no-op where the root logger already has a handler."""
    logging.basicConfig(level=level, format=FORMAT)
    for handler in logging.getLogger().handlers:
        if not any(isinstance(f, RequestIdFilter) for f in handler.filters):
            handler.addFilter(RequestIdFilter())
