import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alloy_api.auth.router import router as auth_router
from alloy_api.config import SettingsDep, get_settings
from alloy_api.crm.router import router as crm_router
from alloy_api.db import DatabaseState, create_database_state
from alloy_api.mail import Mailer, create_mailer
from alloy_api.routers import health
from alloy_api.workspaces.invites import router as invites_router
from alloy_api.workspaces.router import router as workspaces_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi.routing import APIRoute

settings = get_settings()

# Uvicorn configures only its own loggers; this gives the app's a handler and level.
logging.basicConfig(level=settings.log_level, format="%(levelname)s [%(name)s] %(message)s")


class AppState(DatabaseState):
    """What the lifespan puts on `request.state`."""

    mailer: Mailer


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
    """The yielded dict becomes `request.state`. The engine connects lazily."""
    state = AppState(**create_database_state(settings), mailer=create_mailer(settings))
    yield state
    await state["engine"].dispose()


app = FastAPI(
    title=settings.app_name,
    generate_unique_id_function=generate_unique_id,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(invites_router)
app.include_router(crm_router)


@app.get("/")
async def read_root(settings: SettingsDep) -> dict[str, str]:
    return {"app": settings.app_name}
