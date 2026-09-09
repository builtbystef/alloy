from enum import StrEnum
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from alloy_api.crm.models import OwnedByWorkspace

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute
    from sqlalchemy.orm.interfaces import ORMOption

    from alloy_api.workspaces.deps import Membership


class Page(BaseModel):
    """Query parameters every list endpoint takes; filters extend it."""

    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PageOf[T](BaseModel):
    """One page of a list, with the size of the whole list so a client can page it."""

    items: list[T]
    total: int = Field(description="Rows matching the filters, across every page.")
    limit: int
    offset: int

    @classmethod
    def model_parametrized_name(cls, params: tuple[type, ...]) -> str:
        """`PageOf[ContactRead]` is `ContactPage` in the OpenAPI schema."""
        return f"{params[0].__name__.removesuffix('Read')}Page"


def sorted_by[S: Select](
    query: S, column: InstrumentedAttribute, order: SortOrder, tiebreak: InstrumentedAttribute
) -> S:
    """Order by a column, nulls last either way (a missing value sorts after every
    present one), then by a unique column so pages never overlap."""
    expression = column.asc() if order is SortOrder.ASC else column.desc()
    return query.order_by(expression.nulls_last(), tiebreak)


async def paginate[T: BaseModel](
    session: AsyncSession, query: Select, page: Page, schema: type[T]
) -> PageOf[T]:
    """Run a filtered, ordered query twice: once for the count, once for the page."""
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = await session.scalars(query.limit(page.limit).offset(page.offset))
    return PageOf[schema](  # ty: ignore[invalid-type-form]
        items=[schema.model_validate(row) for row in rows],
        total=total or 0,
        limit=page.limit,
        offset=page.offset,
    )


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
