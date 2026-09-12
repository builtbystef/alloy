import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
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
