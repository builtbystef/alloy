import logging
import secrets
from typing import TYPE_CHECKING

from starlette import status
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from alloy_api.logs import request_id

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 128

INTERNAL_ERROR_DETAIL = "Something went wrong. Quote the request ID when reporting it."

# Files go to storage on presigned URLs, never through the API, so its bodies are
# small JSON. The web app's proxy route refuses the same size before buffering.
MAX_BODY_BYTES = 1024 * 1024
BODY_TOO_LARGE_DETAIL = "Request body too large."


def new_request_id() -> str:
    return secrets.token_hex(8)


def _incoming_request_id(scope: Scope) -> str | None:
    """A caller's ID, if it is short printable ASCII (log lines and headers must
    stay clean). `None` to make one."""
    header = REQUEST_ID_HEADER.lower().encode()
    for name, value in scope["headers"]:
        if name == header:
            candidate = value.decode("latin-1").strip()
            if (
                0 < len(candidate) <= _MAX_REQUEST_ID_LENGTH
                and candidate.isascii()
                and candidate.isprintable()
            ):
                return candidate
            return None
    return None


class RequestIdMiddleware:
    """Pure ASGI, so it costs one dict lookup per request rather than a task per
    request like `BaseHTTPMiddleware`. Add it inside CORS so a 500 still gets the
    CORS headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = _incoming_request_id(scope) or new_request_id()
        scope.setdefault("state", {})["request_id"] = rid
        token = request_id.set(rid)
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = message.setdefault("headers", [])
                headers.append((REQUEST_ID_HEADER.lower().encode(), rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            if response_started:
                # Too late for a body of our own; the server closes the connection.
                raise
            log.exception("Unhandled error on %s %s", scope["method"], scope["path"])
            response = JSONResponse(
                {"detail": INTERNAL_ERROR_DETAIL, "request_id": rid},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            await response(scope, receive, send_with_id)
        finally:
            request_id.reset(token)


class BodySizeLimitMiddleware:
    """413 for a body above `limit`: on `Content-Length` before reading anything,
    and on the bytes actually received when the length was not declared."""

    def __init__(self, app: ASGIApp, limit: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope["headers"]:
            if name == b"content-length" and value.isdigit() and int(value) > self.limit:
                response = JSONResponse(
                    {"detail": BODY_TOO_LARGE_DETAIL},
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                )
                await response(scope, receive, send)
                return

        received = 0

        async def receive_limited() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    # Raised inside the endpoint's body read, where Starlette's
                    # exception handling turns it into the 413.
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, BODY_TOO_LARGE_DETAIL)
            return message

        await self.app(scope, receive_limited, send)
