from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from alloy_api.db import SessionDep

router = APIRouter(prefix="/health", tags=["health"])


class Health(BaseModel):
    status: str


@router.get("/")
async def read_health() -> Health:
    """Liveness: the process is up."""
    return Health(status="ok")


@router.get("/db")
async def read_health_db(session: SessionDep) -> Health:
    """Readiness: the database answers a query. 500 if it does not."""
    await session.execute(text("SELECT 1"))
    return Health(status="ok")
