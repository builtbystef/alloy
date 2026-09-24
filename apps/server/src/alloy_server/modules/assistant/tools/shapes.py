"""What the tools return to the model, and the shapes of what they take."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from alloy_server.modules.crm.companies.schemas import CompanyCreate, CompanyUpdate
from alloy_server.modules.crm.contacts.models import ActivityType, ContactStatus
from alloy_server.modules.crm.contacts.schemas import ActivityCreate, ContactCreate, ContactUpdate
from alloy_server.modules.crm.tasks.models import TaskStatus
from alloy_server.modules.crm.tasks.schemas import TaskUpdate

# --- Results -----------------------------------------------------------------------


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    next_page: int | None = Field(
        description="Pass as `page` to get more; null when this is the last."
    )


class ContactRow(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    job_title: str | None
    status: ContactStatus
    company: str | None
    company_id: uuid.UUID | None
    last_contacted_at: datetime | None
    url: str


class CompanyRow(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None
    industry: str | None
    url: str


class CompanySearchRow(CompanyRow):
    contact_count: int
    latest_contact_at: datetime | None = Field(
        description="The most recent `last_contacted_at` among the company's contacts."
    )


class ActivityRow(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    type: ActivityType
    notes: str | None
    created_at: datetime
    logged_by: str | None


class TaskRow(BaseModel):
    id: uuid.UUID
    title: str
    status: TaskStatus
    due_at: datetime | None
    contact: str | None
    contact_id: uuid.UUID | None
    company: str | None
    company_id: uuid.UUID | None
    notes: str | None
    url: str


class AttachmentRow(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    contact_id: uuid.UUID | None
    company_id: uuid.UUID | None
    download_url: str


class ContactDetail(BaseModel):
    contact: ContactRow
    phone: str | None
    recent_activities: list[ActivityRow]
    open_tasks: list[TaskRow]
    attachments: list[AttachmentRow]
    created_at: datetime


class CompanyDetail(BaseModel):
    company: CompanyRow
    notes: str | None
    contacts: list[ContactRow]
    more_contacts: int = Field(description="Contacts beyond the ones listed.")
    attachments: list[AttachmentRow]
    created_at: datetime


class CompanyGroup(BaseModel):
    company: CompanyRow | None = Field(description="Null for contacts without a company.")
    contacts: list[ContactRow]


class GroupedContacts(BaseModel):
    groups: list[CompanyGroup]
    total: int
    page: int
    next_page: int | None


class Skipped(BaseModel):
    name: str
    reason: str
    existing: ContactRow | None = None


class ContactsCreated(BaseModel):
    created: list[ContactRow]
    skipped: list[Skipped]
    attached: list[AttachmentRow]


class CompaniesCreated(BaseModel):
    created: list[CompanyRow]
    attached: list[AttachmentRow]


class Deleted(BaseModel):
    deleted: list[str] = Field(description="Names of what was removed.")


class MemberRow(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str


class WorkspaceInfo(BaseModel):
    id: uuid.UUID
    name: str
    your_role: str
    you_can_write: bool
    today: str
    time_zone: str


# --- Argument shapes ---------------------------------------------------------------


UploadIds = Annotated[
    list[uuid.UUID],
    Field(
        default_factory=list,
        description="Ids of files the user dropped into this chat, to attach to the new record.",
    ),
]


class ContactItem(ContactCreate):
    company_name: str | None = Field(
        None,
        description="Name of an existing company to link, matched case-insensitively. "
        "Prefer `company_id` when known. Create the company first if it does not exist.",
    )
    upload_ids: UploadIds
    allow_duplicate_email: bool = Field(
        default=False,
        description="Create even when a contact with the same email exists. Otherwise the "
        "item is skipped and the existing contact returned, so you can ask the user.",
    )


class CompanyItem(CompanyCreate):
    upload_ids: UploadIds


class ContactChange(BaseModel):
    contact_id: uuid.UUID
    changes: ContactUpdate = Field(
        description="Only the fields to change. A field set to null is cleared."
    )


class CompanyChange(BaseModel):
    company_id: uuid.UUID
    changes: CompanyUpdate = Field(
        description="Only the fields to change. A field set to null is cleared."
    )


class TaskChange(BaseModel):
    task_id: uuid.UUID
    changes: TaskUpdate = Field(
        description="Only the fields to change. `status: done` completes a task, "
        "`status: open` reopens it."
    )


class ActivityItem(ActivityCreate):
    contact_id: uuid.UUID


class FileTarget(BaseModel):
    upload_id: uuid.UUID = Field(description="A file the user dropped into this chat.")
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
