"""The API. `create_app` builds it from a `Settings`; the lifespan opens the
resources once and puts them on `request.state` (dependencies.py reads them from
there)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from alloy_server.config import Settings
from alloy_server.dependencies import SettingsDep
from alloy_server.modules.router import router as api_router
from alloy_server.resources import build_resources
from alloy_server.shared import logs, telemetry
from alloy_server.shared.exceptions import AppError, handle_app_error
from alloy_server.shared.middleware import RequestIdMiddleware
from alloy_server.shared.routing import generate_unique_id

if TYPE_CHECKING:
    from procrastinate.connector import BaseConnector

    from alloy_server.integrations.mail import Mailer
    from alloy_server.integrations.rate_limit import RateLimitStore
    from alloy_server.integrations.storage import ObjectStore


def create_app(
    settings: Settings,
    *,
    mailer: Mailer | None = None,
    object_store: ObjectStore | None = None,
    rate_limit_store: RateLimitStore | None = None,
    jobs_connector: BaseConnector | None = None,
) -> FastAPI:
    """The doubles go to `build_resources`; tests pass an outbox, an in-memory
    store and counters, and an in-memory queue."""
    logs.configure(settings.log_level, settings.log_format)
    if (log_handler := telemetry.configure(settings, service_name="alloy-server")) is not None:
        logging.getLogger().addHandler(log_handler)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[dict[str, object]]:
        """The yielded dict becomes `request.state`."""
        async with build_resources(
            settings,
            mailer=mailer,
            object_store=object_store,
            rate_limit_store=rate_limit_store,
            jobs_connector=jobs_connector,
        ) as resources:
            yield {"resources": resources}

    app = FastAPI(
        title=settings.app_name,
        generate_unique_id_function=generate_unique_id,
        lifespan=lifespan,
    )
    if telemetry.enabled(settings):
        telemetry.instrument_app(app)
        telemetry.instrument_agents()
    # Inside the Logfire span, so the request ID reaches its logs. No CORS and no
    # body limit: browsers only reach the API through the Next.js proxy route,
    # which is same-origin and refuses large bodies itself.
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(AppError, handle_app_error)
    app.include_router(api_router)

    @app.get("/")
    async def read_root(settings: SettingsDep) -> dict[str, str]:
        return {"app": settings.app_name}

    return app
