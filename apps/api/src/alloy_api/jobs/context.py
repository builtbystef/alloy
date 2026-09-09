from contextvars import Token
from typing import TYPE_CHECKING, Any

from taskiq import TaskiqMiddleware

from alloy_api.logs import new_request_id, request_id

if TYPE_CHECKING:
    from taskiq import TaskiqMessage, TaskiqResult

LABEL = "request_id"


class RequestIdMiddleware(TaskiqMiddleware):
    """Sends the request ID in the message labels and sets it for the run.

    A job queued outside a request (the scheduler's) gets a fresh ID, so its lines
    still group; a retry keeps the labels, so it keeps the ID. `pre_execute`, the
    task, and `post_execute` run in one coroutine, so the context variable set
    here is the one the task sees.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tokens: dict[str, Token[str]] = {}

    def pre_send(self, message: TaskiqMessage) -> TaskiqMessage:
        rid = request_id.get()
        if rid != "-":
            message.labels[LABEL] = rid
        return message

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        rid = message.labels.get(LABEL) or new_request_id()
        self._tokens[message.task_id] = request_id.set(rid)
        return message

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult[Any]) -> None:  # noqa: ARG002
        token = self._tokens.pop(message.task_id, None)
        if token is not None:
            request_id.reset(token)
