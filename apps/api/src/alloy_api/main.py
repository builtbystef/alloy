"""The application: settings, logging, the lifespan that opens the shared
resources, the middleware, and the combined router from `api/router.py`."""

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from taskiq import InMemoryBroker

from alloy_api.api.router import router as api_router
from alloy_api.config import SettingsDep, get_settings
from alloy_api.core import logs, telemetry
from alloy_api.core.exceptions import AppError, handle_app_error
from alloy_api.core.middleware import BodySizeLimitMiddleware, RequestIdMiddleware
from alloy_api.db.session import DatabaseState, create_database_state
from alloy_api.integrations.mail import Mailer, create_mailer
from alloy_api.integrations.ratelimit import RateLimitStoreProtocol, create_rate_limit_store
from alloy_api.integrations.storage import ObjectStore, create_object_store
from alloy_api.jobs.broker import broker
from alloy_api.jobs.deps import configure as configure_jobs

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi.routing import APIRoute

settings = get_settings()

logs.configure(settings.log_level, settings.log_format)
if (log_handler := telemetry.configure(settings, service_name="alloy-api")) is not None:
    logging.getLogger().addHandler(log_handler)


class AppState(DatabaseState):
    """What the lifespan puts on `request.state`."""

    mailer: Mailer
    object_store: ObjectStore
    rate_limit_store: RateLimitStoreProtocol


def generate_unique_id(route: APIRoute) -> str:
    """`{tag}-{function}` instead of FastAPI's default `{function}_{path}_{method}`.

    Shorter, stable when a path changes, and the form the FastAPI docs recommend
    for generated clients (packages/api-client). FastAPI raises on duplicates.
    """
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    return route.name


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[AppState]:
    """The yielded dict becomes `request.state`. The engine and the object store
    connect lazily."""
    async with create_object_store(settings) as object_store:
        rate_limit_store = create_rate_limit_store(settings)
        state = AppState(
            **create_database_state(settings),
            mailer=create_mailer(settings),
            object_store=object_store,
            rate_limit_store=rate_limit_store,
        )
        if isinstance(broker, InMemoryBroker):
            # No worker: this process runs the jobs, with the app's own resources.
            configure_jobs(
                broker.state,
                settings=settings,
                session_factory=state["session_factory"],
                mailer=state["mailer"],
                object_store=object_store,
            )
        await broker.startup()
        yield state
        await broker.shutdown()
        await rate_limit_store.aclose()
        await state["engine"].dispose()


app = FastAPI(
    title=settings.app_name,
    generate_unique_id_function=generate_unique_id,
    lifespan=lifespan,
)
if telemetry.enabled(settings):
    telemetry.instrument_app(app)
    telemetry.instrument_agents()
# Innermost: inside the Logfire span, so the request ID reaches its logs, and
# inside CORS, so a 500 still carries the CORS headers.
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, handle_app_error)
app.include_router(api_router)


@app.get("/")
async def read_root(settings: SettingsDep) -> dict[str, str]:
    return {"app": settings.app_name}
