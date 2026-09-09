import logging
from contextlib import AsyncExitStack

from taskiq import TaskiqEvents, TaskiqState

from alloy_api import logs, telemetry
from alloy_api.config import get_settings
from alloy_api.jobs import create_broker, create_scheduler
from alloy_api.jobs.deps import open_resources

logger = logging.getLogger(__name__)

settings = get_settings()

# The worker's child processes start with no log handler (Taskiq configures one
# only for the `spawn` start method, and Python 3.14 forks with `forkserver`), so
# the app's loggers, the console mailer included, would print nothing.
logs.configure(settings.log_level, settings.log_format)

broker = create_broker(settings)
scheduler = create_scheduler(broker, settings)

_resources = AsyncExitStack()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    # The in-memory broker fires this in the API process too; there the lifespan
    # has already put the app's own resources on the state.
    if not broker.is_worker_process:
        return
    # Here, not at import: the API and the scheduler import this module too, and
    # the exporter's threads must start in this child process, not before the fork.
    if (log_handler := telemetry.configure(settings, service_name="alloy-worker")) is not None:
        logging.getLogger().addHandler(log_handler)
    await open_resources(state, settings, _resources)
    logger.info("Worker ready: %d tasks registered", len(broker.get_all_tasks()))


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def on_worker_shutdown(_state: TaskiqState) -> None:
    await _resources.aclose()


# The tasks decorate `broker`, so they are imported last, and here rather than
# by `--fs-discover`, so the worker, the scheduler, and the API all see the same set.
from alloy_api.jobs import emails as _emails  # noqa: E402, F401
from alloy_api.jobs import imports as _imports  # noqa: E402, F401
from alloy_api.jobs import purge as _purge  # noqa: E402, F401
