import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from alloy_server.config import SettingsDep, get_settings
from alloy_server.db.session import DatabaseState, create_database_state
from alloy_server.integrations.mail import Mailer, create_mailer
from alloy_server.integrations.rate_limit import DatabaseRateLimitStore, RateLimitStore
from alloy_server.integrations.storage import ObjectStore, create_object_store
from alloy_server.jobs.app import app as jobs
from alloy_server.modules.router import router as api_router
from alloy_server.shared import logs, telemetry
from alloy_server.shared.exceptions import AppError, handle_app_error
from alloy_server.shared.middleware import RequestIdMiddleware
from alloy_server.shared.routing import generate_unique_id

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

settings = get_settings()

logs.configure(settings.log_level, settings.log_format)
if (log_handler := telemetry.configure(settings, service_name="alloy-server")) is not None:
    logging.getLogger().addHandler(log_handler)


class AppState(DatabaseState):
    """What the lifespan puts on `request.state`."""

    mailer: Mailer
    object_store: ObjectStore
    rate_limit_store: RateLimitStore


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[AppState]:
    """The yielded dict becomes `request.state`. The engine and the object store
    connect lazily; `jobs` opens the pool it queues through."""
    async with create_object_store(settings) as object_store, jobs.open_async():
        database = create_database_state(settings)
        state = AppState(
            **database,
            mailer=create_mailer(settings),
            object_store=object_store,
            rate_limit_store=DatabaseRateLimitStore(database["session_factory"]),
        )
        yield state
        await state["engine"].dispose()


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
