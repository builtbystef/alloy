import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from alloy_api.models import Base, Timestamps, UUIDPrimaryKey, string_enum

if TYPE_CHECKING:
    # Imported lazily: alloy_api.models imports this module while auth.models loads.
    from alloy_api.auth.models import User


class ContactStatus(StrEnum):
    LEAD = "lead"
    ACTIVE = "active"
    INACTIVE = "inactive"


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


class ImportKind(StrEnum):
    CONTACTS = "contacts"
    COMPANIES = "companies"


class ImportStatus(StrEnum):
    """`pending` until the client reports the CSV uploaded, `queued` once the job is
    sent, `running` while the worker reads the file, then `done` or `failed`."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ActivityType(StrEnum):
    NOTE = "note"
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    TASK_COMPLETED = "task_completed"


# Logging one of these counts as contacting the person.
CONTACT_ACTIVITY_TYPES = frozenset(
    {ActivityType.CALL, ActivityType.EMAIL, ActivityType.MEETING, ActivityType.FOLLOW_UP}
)


class OwnedByWorkspace(UUIDPrimaryKey):
    """Every CRM row belongs to one workspace, and every query filters on it."""

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, sort_order=-99
    )


class CreatedBy:
    """Who made the row. Null for rows that predate the column, and once the user
    is gone. Loaded with the row: every read shows it."""

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), sort_order=90
    )

    @declared_attr
    def created_by(self) -> Mapped[User | None]:
        return relationship("User", lazy="selectin")


class Company(OwnedByWorkspace, CreatedBy, Timestamps, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")


class Contact(OwnedByWorkspace, CreatedBy, Timestamps, Base):
    __tablename__ = "contacts"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    job_title: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[ContactStatus] = mapped_column(
        string_enum(ContactStatus), default=ContactStatus.LEAD
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company | None] = relationship(back_populates="contacts")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )


class Activity(UUIDPrimaryKey, CreatedBy, Base):
    """One entry in a contact's feed. Owned through the contact. `created_by` is
    who logged it, or who completed the task for a `task_completed` entry."""

    __tablename__ = "activities"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[ActivityType] = mapped_column(string_enum(ActivityType))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    contact: Mapped[Contact] = relationship(back_populates="activities")


class Task(OwnedByWorkspace, CreatedBy, Timestamps, Base):
    __tablename__ = "tasks"

    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[TaskStatus] = mapped_column(string_enum(TaskStatus), default=TaskStatus.OPEN)
    notes: Mapped[str | None] = mapped_column(Text)

    contact: Mapped[Contact | None] = relationship()
    company: Mapped[Company | None] = relationship()


class Attachment(OwnedByWorkspace, Timestamps, Base):
    """A file on a contact or a company. The bytes live in object storage under
    `key`; this row is the metadata.

    Created before the upload, with `uploaded_at` null, when the API hands out the
    upload URL; stamped once the client reports the upload done and the object is
    found in the store. Lists show only uploaded rows.
    """

    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint("(contact_id IS NULL) <> (company_id IS NULL)", name="one_parent"),
    )

    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger)
    key: Mapped[str] = mapped_column(String(512), unique=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    uploaded_by: Mapped["User | None"] = relationship()


class Import(OwnedByWorkspace, Timestamps, Base):
    """A CSV of contacts or companies being loaded into the workspace by a job.

    Created with the upload URL, like an attachment; `start` sends the job once the
    file is in the store under `key`. The job records what it did here: the row
    counts, the first `MAX_ROW_ERRORS` rows it could not load as `{row, message}`,
    and `error` if it could not finish at all. The file is removed when it ends.
    """

    __tablename__ = "imports"

    kind: Mapped[ImportKind] = mapped_column(string_enum(ImportKind))
    status: Mapped[ImportStatus] = mapped_column(
        string_enum(ImportStatus), default=ImportStatus.PENDING
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger)
    key: Mapped[str] = mapped_column(String(512), unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_rows: Mapped[int] = mapped_column(default=0)
    created_count: Mapped[int] = mapped_column(default=0)
    skipped_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    errors: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)

    requested_by: Mapped["User | None"] = relationship()
