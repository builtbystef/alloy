from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from alloy_server.crm.companies.schemas import CompanyRef
from alloy_server.crm.contacts.schemas import ContactRef
from alloy_server.crm.dates import UTC_ZONE, DueFilter, TimeZoneField
from alloy_server.crm.models import RowSource
from alloy_server.crm.pagination import Page, SortOrder
from alloy_server.crm.schemas import Name, Notes, NotNull, ReadModel, UserRef
from alloy_server.crm.tasks.models import TaskStatus

ContactLink = Annotated[UUID | None, Field(description="Links the task to a person.")]
CompanyLink = Annotated[
    UUID | None, Field(description="Links the task to a company with no particular person.")
]


class TaskCreate(BaseModel):
    title: Name
    due_at: AwareDatetime | None = None
    status: TaskStatus = TaskStatus.OPEN
    contact_id: ContactLink = None
    company_id: CompanyLink = None
    notes: Notes | None = None


class TaskUpdate(BaseModel):
    """Setting `contact_id` unlinks the company and vice versa: the link moves."""

    title: Annotated[Name | None, NotNull] = None
    due_at: AwareDatetime | None = None
    status: Annotated[TaskStatus | None, NotNull] = None
    contact_id: ContactLink = None
    company_id: CompanyLink = None
    notes: Notes | None = None


class TaskRead(ReadModel):
    id: UUID
    title: str
    due_at: datetime | None
    status: TaskStatus
    notes: str | None
    contact: ContactRef | None
    company: CompanyRef | None = Field(
        validation_alias="linked_company",
        description="The company the task is about: its own, or its contact's.",
    )
    created_by: UserRef | None
    source: RowSource | None = Field(
        description="Set when the assistant or an import made the row."
    )
    created_at: datetime
    updated_at: datetime


class TaskSort(StrEnum):
    DUE_AT = "due_at"
    TITLE = "title"
    CONTACT = "contact"
    COMPANY = "company"


class TaskFilters(Page):
    """`due` and `status` filter independently: pass both for open overdue tasks."""

    due: DueFilter | None = None
    tz: TimeZoneField = UTC_ZONE
    status: TaskStatus | None = None
    contact_id: UUID | None = None
    company_id: UUID | None = Field(
        None, description="Tasks linked to the company, or to one of its contacts."
    )
    sort: TaskSort = TaskSort.DUE_AT
    order: SortOrder = SortOrder.ASC
