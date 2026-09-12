from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_api.crm.models import CreatedBy, OwnedByWorkspace
from alloy_api.db.base import Base, Timestamps

if TYPE_CHECKING:
    from alloy_api.crm.contacts.models import Contact


class Company(OwnedByWorkspace, CreatedBy, Timestamps, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")
