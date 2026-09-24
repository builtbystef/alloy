from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from alloy_server.modules.workspaces.models import WorkspaceRole
from alloy_server.modules.workspaces.permissions import Permission

WorkspaceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: WorkspaceName


class WorkspaceUpdate(BaseModel):
    name: WorkspaceName


class WorkspaceResponse(ResponseModel):
    """A workspace as seen by one member: their role and what it allows come along."""

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    onboarded_at: datetime | None
    role: WorkspaceRole
    permissions: list[Permission]


class MemberResponse(ResponseModel):
    id: UUID
    user_id: UUID
    email: str
    role: WorkspaceRole
    created_at: datetime


class MemberUpdate(BaseModel):
    role: WorkspaceRole


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
