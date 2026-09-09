import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from alloy_api import telemetry
from alloy_api.config import SettingsDep
from alloy_api.db import SessionDep
from alloy_api.jobs import ping_redis
from alloy_api.storage import ObjectStoreDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class Health(BaseModel):
    status: str


async def probe(name: str, check: Callable[[], Awaitable[object]]) -> Health:
    with telemetry.quiet():
        try:
            await check()
        except Exception as exc:  # noqa: BLE001 - any failure means not ready
            logger.warning("Health check %s failed: %s", name, exc)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, f"{name} is unavailable"
            ) from None
    return Health(status="ok")


@router.get("/")
async def read_health() -> Health:
    """Liveness: the process is up."""
    return Health(status="ok")


@router.get("/db")
async def read_health_db(session: SessionDep) -> Health:
    """Readiness: the database answers."""
    return await probe("database", lambda: session.execute(text("SELECT 1")))


@router.get("/redis")
async def read_health_redis(settings: SettingsDep) -> Health:
    """Readiness: the Redis behind the job queue answers. Always ok on the in-memory
    broker, which needs no Redis."""
    if settings.jobs_broker != "redis":
        return Health(status="ok")
    return await probe("redis", lambda: ping_redis(str(settings.redis_url), settings.redis_timeout))


@router.get("/storage")
async def read_health_storage(store: ObjectStoreDep) -> Health:
    """Readiness: the object store answers and the bucket exists."""
    return await probe("storage", store.ping)
