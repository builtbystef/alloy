from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from alloy_server.db.base import Base


class RateLimitWindow(Base):
    """One fixed window: hits on `key` until `expires_at`. UNLOGGED: the counters
    are written on every login attempt and are worthless after a crash anyway,
    so they skip the write-ahead log."""

    __tablename__ = "rate_limit_windows"
    __table_args__ = {"prefixes": ["UNLOGGED"]}  # noqa: RUF012 - how SQLAlchemy takes it

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    count: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
