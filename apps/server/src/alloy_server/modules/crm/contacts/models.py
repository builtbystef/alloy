import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_server.db.base import Base, Timestamps, UUIDPrimaryKey, string_enum
from alloy_server.modules.crm.companies.models import Company
from alloy_server.modules.crm.models import CreatedBy, OwnedByWorkspace


class ContactStatus(StrEnum):
    LEAD = "lead"
    ACTIVE = "active"
    INACTIVE = "inactive"


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
