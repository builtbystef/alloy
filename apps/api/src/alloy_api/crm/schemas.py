"""Request and response bodies. `*Update` models are PATCH bodies: fields left out are
untouched, fields sent as `null` are cleared.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, HttpUrl, StringConstraints

from alloy_api.crm.models import ActivityType, ContactStatus, TaskStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]
Industry = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


def check_url(value: str) -> str:
    """Validated as an http(s) URL, stored as typed (no trailing slash added)."""
    HttpUrl(value)
    return value


Website = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500), AfterValidator(check_url)
]


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CompanyCreate(BaseModel):
    name: Name
    website: Website | None = None
    industry: Industry | None = None
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: Name | None = None
    website: Website | None = None
    industry: Industry | None = None
    notes: str | None = None


class CompanyRef(ReadModel):
    """Enough to link to a company from a contact or task."""

    id: UUID
    name: str


class CompanyRead(CompanyRef):
    website: str | None
    industry: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


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
    created_at: datetime
    updated_at: datetime


class ActivityCreate(BaseModel):
    type: ActivityType
    notes: str | None = None


class ActivityRead(ReadModel):
    id: UUID
    contact_id: UUID
    type: ActivityType
    notes: str | None
    created_at: datetime


class TaskCreate(BaseModel):
    title: Name
    due_at: datetime | None = None
    status: TaskStatus = TaskStatus.OPEN
    contact_id: UUID | None = None
    company_id: UUID | None = None
    notes: str | None = None


class TaskUpdate(BaseModel):
    title: Name | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None
    contact_id: UUID | None = None
    company_id: UUID | None = None
    notes: str | None = None


class TaskRead(ReadModel):
    id: UUID
    title: str
    due_at: datetime | None
    status: TaskStatus
    notes: str | None
    contact: ContactRef | None
    company: CompanyRef | None
    created_at: datetime
    updated_at: datetime


class Dashboard(BaseModel):
    total_contacts: int
    tasks_due_today: int
    overdue_tasks: int
    recently_contacted: list[ContactRead]
    not_recently_contacted: list[ContactRead]
