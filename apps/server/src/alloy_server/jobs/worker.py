import asyncio
import logging
from contextlib import AsyncExitStack

from alloy_server.config import get_settings
from alloy_server.core import logs, telemetry
from alloy_server.jobs.app import app
from alloy_server.jobs.resources import open_resources, worker_context

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    logs.configure(settings.log_level, settings.log_format)
    if (log_handler := telemetry.configure(settings, service_name="alloy-worker")) is not None:
        logging.getLogger().addHandler(log_handler)
    app.perform_import_paths()
    async with AsyncExitStack() as stack:
        resources = await open_resources(settings, stack)
        async with app.open_async():
            logger.info("Worker ready: %d tasks registered", len(app.tasks))
            await app.run_worker_async(
                concurrency=settings.jobs_concurrency,
                additional_context=worker_context(resources),
            )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
