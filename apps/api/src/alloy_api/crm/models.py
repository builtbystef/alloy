import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from alloy_api.db.base import UUIDPrimaryKey, string_enum

if TYPE_CHECKING:
    # Imported lazily: alloy_api.db.base imports this module while auth.models loads.
    from alloy_api.auth.models import User


class RowSource(StrEnum):
    """How a row came to be, when not typed in by hand: the assistant or a CSV import.
    Null for rows made in the UI."""

    AGENT = "agent"
    IMPORT = "import"


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
    source: Mapped[RowSource | None] = mapped_column(string_enum(RowSource), sort_order=91)

    @declared_attr
    def created_by(self) -> Mapped[User | None]:
        return relationship("User", lazy="selectin")
