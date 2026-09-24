from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from alloy_server.crm.models import RowSource
from alloy_server.crm.pagination import Page, SortOrder
from alloy_server.crm.schemas import Industry, Name, Notes, NotNull, ResponseModel, UserRef, Website


class CompanyCreate(BaseModel):
    name: Name
    website: Website | None = None
    industry: Industry | None = None
    notes: Notes | None = None


class CompanyUpdate(BaseModel):
    name: Annotated[Name | None, NotNull] = None
    website: Website | None = None
    industry: Industry | None = None
    notes: Notes | None = None


class CompanyRef(ResponseModel):
    id: UUID
    name: str


class CompanyResponse(CompanyRef):
    website: str | None
    industry: str | None
    notes: str | None
    created_by: UserRef | None
    source: RowSource | None = Field(
        description="Set when the assistant or an import made the row."
    )
    created_at: datetime
    updated_at: datetime


class CompanySort(StrEnum):
    NAME = "name"
    INDUSTRY = "industry"
    CREATED_AT = "created_at"


class CompanyFilters(Page):
    q: str | None = Field(None, description="Matches name, website, or industry.")
    sort: CompanySort = CompanySort.NAME
    order: SortOrder = SortOrder.ASC
