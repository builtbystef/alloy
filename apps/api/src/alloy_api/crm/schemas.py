"""Request and response bodies. `*Update` models are PATCH bodies: fields left out are
untouched, fields sent as `null` are cleared.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
)

from alloy_api.crm.models import ActivityType, ContactStatus, ImportKind, ImportStatus, TaskStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]
Industry = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
Notes = Annotated[str, StringConstraints(max_length=10_000)]


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
    notes: Notes | None = None


class CompanyUpdate(BaseModel):
    name: Name | None = None
    website: Website | None = None
    industry: Industry | None = None
    notes: Notes | None = None


class UserRef(ReadModel):
    """Enough to name the user who made or uploaded something."""

    id: UUID
    email: str


class CompanyRef(ReadModel):
    """Enough to link to a company from a contact or task."""

    id: UUID
    name: str


class CompanyRead(CompanyRef):
    website: str | None
    industry: str | None
    notes: str | None
    created_by: UserRef | None
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
    created_by: UserRef | None
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
    created_at: datetime


class TaskCreate(BaseModel):
    title: Name
    due_at: datetime | None = None
    status: TaskStatus = TaskStatus.OPEN
    contact_id: UUID | None = None
    company_id: UUID | None = None
    notes: Notes | None = None


class TaskUpdate(BaseModel):
    title: Name | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None
    contact_id: UUID | None = None
    company_id: UUID | None = None
    notes: Notes | None = None


class TaskRead(ReadModel):
    id: UUID
    title: str
    due_at: datetime | None
    status: TaskStatus
    notes: str | None
    contact: ContactRef | None
    company: CompanyRef | None
    created_by: UserRef | None
    created_at: datetime
    updated_at: datetime


class Dashboard(BaseModel):
    total_contacts: int
    tasks_due_today: int
    overdue_tasks: int
    recently_contacted: list[ContactRead]
    not_recently_contacted: list[ContactRead]


Filename = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
# `type/subtype`, as the browser reports it. The store pins the upload to it.
ContentType = Annotated[str, StringConstraints(max_length=255, pattern=r"^[\w.+-]+/[\w.+-]+$")]


class AttachmentCreate(BaseModel):
    """What the client knows before uploading. `size` is checked against the limit
    here and again against the stored object on completion."""

    filename: Filename
    content_type: ContentType
    size: int = Field(ge=1, description="Bytes.")


class AttachmentRead(ReadModel):
    id: UUID
    contact_id: UUID | None
    company_id: UUID | None
    filename: str
    content_type: str
    size: int
    uploaded_by: UserRef | None
    uploaded_at: datetime | None
    created_at: datetime


class AttachmentUpload(BaseModel):
    """Step one of an upload: `PUT` the file to `upload_url` with the `Content-Type`
    and `size` given at creation (the URL accepts nothing else), then
    `POST .../attachments/{id}/complete`."""

    attachment: AttachmentRead
    upload_url: str
    expires_at: datetime


class ImportCreate(BaseModel):
    """What the client knows before uploading the CSV."""

    kind: ImportKind
    filename: Filename
    size: int = Field(ge=1, description="Bytes.")


class RowError(BaseModel):
    row: int = Field(description="Line number in the file; the header is line 1.")
    message: str


class ImportRead(ReadModel):
    id: UUID
    kind: ImportKind
    status: ImportStatus
    filename: str
    size: int
    requested_by: UserRef | None
    started_at: datetime | None
    finished_at: datetime | None
    total_rows: int
    created_count: int
    skipped_count: int
    failed_count: int
    errors: list[RowError]
    error: str | None = Field(description="Why the import could not finish, if it could not.")
    created_at: datetime


class ImportUpload(BaseModel):
    """Step one of an import: `PUT` the CSV to `upload_url` as `text/csv` with the
    `size` given at creation, then `POST .../imports/{id}/start`."""

    import_: ImportRead = Field(alias="import")
    upload_url: str
    expires_at: datetime

    model_config = ConfigDict(populate_by_name=True)
