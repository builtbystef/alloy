from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from alloy_api.config import SettingsDep
from alloy_api.db import SessionDep
from alloy_api.jobs import ping_redis

router = APIRouter(prefix="/health", tags=["health"])


class Health(BaseModel):
    status: str


@router.get("/")
async def read_health() -> Health:
    """Liveness: the process is up."""
    return Health(status="ok")


@router.get("/db")
async def read_health_db(session: SessionDep) -> Health:
    """Readiness: the database answers."""
    await session.execute(text("SELECT 1"))
    return Health(status="ok")


@router.get("/redis")
async def read_health_redis(settings: SettingsDep) -> Health:
    """Readiness: the Redis behind the job queue answers. Always ok on the in-memory
    broker, which needs no Redis."""
    if settings.jobs_broker == "redis":
        await ping_redis(str(settings.redis_url))
    return Health(status="ok")
