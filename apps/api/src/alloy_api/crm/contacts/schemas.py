from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from alloy_api.crm.companies.schemas import CompanyRef
from alloy_api.crm.contacts.models import ActivityType, ContactStatus
from alloy_api.crm.models import RowSource
from alloy_api.crm.pagination import Page, SortOrder
from alloy_api.crm.schemas import Name, Notes, Phone, ReadModel, Short, UserRef


class ContactCreate(BaseModel):
    name: Name
    email: EmailStr | None = None
    phone: Phone | None = None
    job_title: Short | None = None
    company_id: UUID | None = None
    status: ContactStatus = ContactStatus.LEAD
    last_contacted_at: datetime | None = None


class ContactUpdate(BaseModel):
    name: Name | None = None
    email: EmailStr | None = None
    phone: Phone | None = None
    job_title: Short | None = None
    company_id: UUID | None = None
    status: ContactStatus | None = None
    last_contacted_at: datetime | None = None


class ContactRef(ReadModel):
    id: UUID
    name: str


class ContactRead(ContactRef):
    email: str | None
    phone: str | None
    job_title: str | None
    status: ContactStatus
    last_contacted_at: datetime | None
    company: CompanyRef | None
    created_by: UserRef | None
    source: RowSource | None = Field(
        description="Set when the assistant or an import made the row."
    )
    created_at: datetime
    updated_at: datetime


class ActivityCreate(BaseModel):
    type: ActivityType
    notes: Notes | None = None


class ActivityRead(ReadModel):
    id: UUID
    contact_id: UUID
    type: ActivityType
    notes: str | None
    created_by: UserRef | None = Field(
        description="Who logged it; for `task_completed`, who completed the task."
    )
    source: RowSource | None = Field(description="Set when the assistant logged it.")
    created_at: datetime


class ContactSort(StrEnum):
    NAME = "name"
    COMPANY = "company"
    STATUS = "status"
    LAST_CONTACTED_AT = "last_contacted_at"


class ContactFilters(Page):
    q: str | None = Field(None, description="Matches name, email, phone, job title, or company.")
    status: ContactStatus | None = None
    company_id: UUID | None = None
    sort: ContactSort = ContactSort.NAME
    order: SortOrder = SortOrder.ASC
