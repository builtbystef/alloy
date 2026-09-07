from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class Health(BaseModel):
    status: str


@router.get("/")
async def read_health() -> Health:
    return Health(status="ok")
