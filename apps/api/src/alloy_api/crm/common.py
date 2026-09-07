from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from alloy_api.crm.models import OwnedByWorkspace

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm.interfaces import ORMOption

    from alloy_api.workspaces.deps import Membership


class Page(BaseModel):
    """Query parameters every list endpoint takes; filters extend it."""

    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


def not_found(model: type[OwnedByWorkspace]) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")


async def fetch_owned[T: OwnedByWorkspace](
    session: AsyncSession,
    model: type[T],
    object_id: UUID,
    membership: Membership,
    *options: ORMOption,
) -> T:
    """The row with this id, if it is in the caller's workspace; 404 otherwise, so ids
    leak nothing."""
    row = await session.scalar(
        select(model)
        .options(*options)
        .where(model.id == object_id)
        .where(model.workspace_id == membership.workspace.id)
    )
    if row is None:
        raise not_found(model)
    return row


async def check_owned(
    session: AsyncSession,
    model: type[OwnedByWorkspace],
    object_id: UUID | None,
    membership: Membership,
) -> None:
    """A referenced id in a body (`company_id`, ...) must be in the same workspace."""
    if object_id is not None:
        await fetch_owned(session, model, object_id, membership)
