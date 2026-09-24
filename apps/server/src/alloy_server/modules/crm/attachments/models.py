import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_server.db.base import Base, Timestamps
from alloy_server.modules.crm.models import OwnedByWorkspace

if TYPE_CHECKING:
    from alloy_server.modules.auth.models import User


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
