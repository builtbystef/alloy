from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from alloy_api.workspaces.models import WorkspaceRole
from alloy_api.workspaces.permissions import Permission

WorkspaceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: WorkspaceName


class WorkspaceUpdate(BaseModel):
    name: WorkspaceName


class WorkspaceRead(ReadModel):
    """A workspace as seen by one member: their role and what it allows come along."""

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    role: WorkspaceRole
    permissions: list[Permission]


class MemberRead(ReadModel):
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


class InviteRead(ReadModel):
    id: UUID
    email: str
    role: WorkspaceRole
    invited_by: str | None
    created_at: datetime
    expires_at: datetime


class InvitePreview(BaseModel):
    """What the invitation page shows before the invitee logs in or signs up."""

    workspace_name: str
    email: str
    role: WorkspaceRole
    invited_by: str | None
    expires_at: datetime
