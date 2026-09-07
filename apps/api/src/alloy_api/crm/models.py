import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_api.models import Base, Timestamps, UUIDPrimaryKey


class ContactStatus(StrEnum):
    LEAD = "lead"
    ACTIVE = "active"
    INACTIVE = "inactive"


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


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


def string_enum[E: StrEnum](enum_type: type[E]) -> Enum:
    """A VARCHAR holding the member values (not names), so adding a member needs no migration.

    No PostgreSQL enum type and no CHECK constraint: the API validates the values.
    """
    return Enum(
        enum_type,
        native_enum=False,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )


class OwnedByUser(UUIDPrimaryKey):
    """Every CRM row belongs to one user, and every query filters on it."""

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, sort_order=-99
    )


class Company(OwnedByUser, Timestamps, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")


class Contact(OwnedByUser, Timestamps, Base):
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


class Activity(UUIDPrimaryKey, Base):
    """One entry in a contact's feed. Owned through the contact."""

    __tablename__ = "activities"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[ActivityType] = mapped_column(string_enum(ActivityType))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    contact: Mapped[Contact] = relationship(back_populates="activities")


class Task(OwnedByUser, Timestamps, Base):
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
