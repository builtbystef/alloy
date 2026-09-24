from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

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
