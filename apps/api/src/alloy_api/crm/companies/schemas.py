from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from alloy_api.crm.models import RowSource
from alloy_api.crm.pagination import Page, SortOrder
from alloy_api.crm.schemas import Industry, Name, Notes, ReadModel, UserRef, Website


class CompanyCreate(BaseModel):
    name: Name
    website: Website | None = None
    industry: Industry | None = None
    notes: Notes | None = None


class CompanyUpdate(BaseModel):
    name: Name | None = None
    website: Website | None = None
    industry: Industry | None = None
    notes: Notes | None = None


class CompanyRef(ReadModel):
    id: UUID
    name: str


class CompanyRead(CompanyRef):
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
