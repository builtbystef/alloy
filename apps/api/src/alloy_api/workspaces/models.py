import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_api.models import Base, Timestamps, UUIDPrimaryKey, string_enum

if TYPE_CHECKING:
    # Imported lazily: alloy_api.models imports this module while auth.models loads.
    from alloy_api.auth.models import User


class WorkspaceRole(StrEnum):
    """Ordered from most to least powerful; see permissions.py for what each may do."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Workspace(UUIDPrimaryKey, Timestamps, Base):
    """The unit every business entity belongs to. Deleting one takes everything in it."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(100))

    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", passive_deletes=True
    )
    invites: Mapped[list["WorkspaceInvite"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", passive_deletes=True
    )


class WorkspaceMember(UUIDPrimaryKey, Timestamps, Base):
    """A user's seat in a workspace, with one role. A user has at most one seat per workspace."""

    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[WorkspaceRole] = mapped_column(string_enum(WorkspaceRole))

    workspace: Mapped[Workspace] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class WorkspaceInvite(UUIDPrimaryKey, Base):
    """An emailed link that grants a seat. The email holds a random token; only its
    SHA-256 is stored here.

    Pending while `accepted_at` and `revoked_at` are null and `expires_at` is in the
    future. Accepting or revoking stamps the row rather than deleting it.
    """

    __tablename__ = "workspace_invites"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    # Stored lower-cased; must match the accepting user's email.
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[WorkspaceRole] = mapped_column(string_enum(WorkspaceRole))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workspace: Mapped[Workspace] = relationship(back_populates="invites")
    invited_by: Mapped["User | None"] = relationship()
