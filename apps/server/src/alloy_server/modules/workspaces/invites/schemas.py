from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from alloy_server.modules.workspaces.models import WorkspaceRole
from alloy_server.modules.workspaces.schemas import ResponseModel


class InviteCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class InviteResponse(ResponseModel):
    """As the workspace's admins see it: pending, or declined by the invitee."""

    id: UUID
    email: str
    role: WorkspaceRole
    invited_by: str | None
    created_at: datetime
    expires_at: datetime
    declined_at: datetime | None


class InvitePreview(BaseModel):
    """What the invitation page shows before the invitee logs in or signs up."""

    workspace_name: str
    email: str
    role: WorkspaceRole
    invited_by: str | None
    expires_at: datetime


class PendingInviteResponse(InvitePreview):
    """One of the caller's own, by id: the token is not stored, so this is how the
    app accepts or declines one without the link."""

    id: UUID
