from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute


class Page(BaseModel):
    """Query parameters every list endpoint takes; filters extend it."""

    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PageOf[T](BaseModel):
    items: list[T]
    total: int = Field(description="Rows matching the filters, across every page.")
    limit: int
    offset: int

    @classmethod
    def model_parametrized_name(cls, params: tuple[type, ...]) -> str:
        """`PageOf[ContactResponse]` is `ContactPage` in the OpenAPI schema."""
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
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = await session.scalars(query.limit(page.limit).offset(page.offset))
    return PageOf[schema](  # ty: ignore[invalid-type-form]
        items=[schema.model_validate(row) for row in rows],
        total=total or 0,
        limit=page.limit,
        offset=page.offset,
    )
