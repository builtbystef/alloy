from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from alloy_api.crm.models import OwnedByUser

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm.interfaces import ORMOption

    from alloy_api.auth.models import User


class Page(BaseModel):
    """Query parameters every list endpoint takes; filters extend it."""

    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


def not_found(model: type[OwnedByUser]) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")


async def fetch_owned[T: OwnedByUser](
    session: AsyncSession,
    model: type[T],
    object_id: UUID,
    user: User,
    *options: ORMOption,
) -> T:
    """The row with this id, if it belongs to `user`; 404 otherwise, so ids leak nothing."""
    row = await session.scalar(
        select(model).options(*options).where(model.id == object_id).where(model.user_id == user.id)
    )
    if row is None:
        raise not_found(model)
    return row


async def check_owned(
    session: AsyncSession, model: type[OwnedByUser], object_id: UUID | None, user: User
) -> None:
    """A referenced id in a body (`company_id`, ...) must be the caller's own row."""
    if object_id is not None:
        await fetch_owned(session, model, object_id, user)
