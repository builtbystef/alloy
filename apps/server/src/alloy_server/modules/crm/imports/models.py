import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_server.db.base import Base, Timestamps, string_enum
from alloy_server.modules.crm.models import OwnedByWorkspace

if TYPE_CHECKING:
    from alloy_server.modules.auth.models import User


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
