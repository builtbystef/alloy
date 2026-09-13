import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_server.crm.companies.models import Company
from alloy_server.crm.contacts.models import Contact
from alloy_server.crm.models import CreatedBy, OwnedByWorkspace
from alloy_server.db.base import Base, Timestamps, string_enum


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


class Task(OwnedByWorkspace, CreatedBy, Timestamps, Base):
    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("contact_id IS NULL OR company_id IS NULL", name="one_link"),)

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

    @property
    def linked_company(self) -> Company | None:
        """The company the task is about: its own, or its contact's. Needs
        `contact.company` loaded (`WITH_RELATIONS` in the service)."""
        if self.contact is not None:
            return self.contact.company
        return self.company
