from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alloy_api.config import SettingsDep, get_settings
from alloy_api.routers import health

if TYPE_CHECKING:
    from fastapi.routing import APIRoute

settings = get_settings()


def generate_unique_id(route: APIRoute) -> str:
    """`{tag}-{function}` instead of FastAPI's default `{function}_{path}_{method}`.

    Shorter, stable when a path changes, and the form the FastAPI docs recommend
    for generated clients (packages/api-client). FastAPI raises on duplicates.
    """
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    return route.name


app = FastAPI(title=settings.app_name, generate_unique_id_function=generate_unique_id)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)


@app.get("/")
async def read_root(settings: SettingsDep) -> dict[str, str]:
    return {"app": settings.app_name}
