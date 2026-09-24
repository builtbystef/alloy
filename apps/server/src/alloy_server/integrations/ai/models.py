import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from alloy_server.db.base import Base, UUIDPrimaryKey


class ModelCall(UUIDPrimaryKey, Base):
    """One request to a model: who made it, from which feature, and what it cost
    in tokens. The app's own record, for quotas and per-workspace reporting;
    Logfire sees the same numbers, for debugging.

    Points at the workspace and user by table, not by import, so the integration
    depends on no module. `source` names the feature (`assistant`), and
    `request_id` ties the row to that request's log lines."""

    __tablename__ = "model_calls"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cache_read_tokens: Mapped[int]
    cache_write_tokens: Mapped[int]
    request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
