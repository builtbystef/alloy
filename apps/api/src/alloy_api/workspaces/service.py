"""Workspace operations shared by more than one router (signup also creates one)."""

from typing import TYPE_CHECKING

from alloy_api.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from alloy_api.workspaces.permissions import permissions_for
from alloy_api.workspaces.schemas import InviteRead, MemberRead, WorkspaceRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.auth.models import User
    from alloy_api.workspaces.deps import Membership
    from alloy_api.workspaces.models import WorkspaceInvite

DEFAULT_WORKSPACE_NAME = "My Workspace"


def create_workspace(session: AsyncSession, name: str, owner: User) -> WorkspaceMember:
    """A new workspace with `owner` in the owner seat. Flushed, not committed."""
    workspace = Workspace(name=name)
    member = WorkspaceMember(workspace=workspace, user=owner, role=WorkspaceRole.OWNER)
    session.add_all([workspace, member])
    return member


def workspace_read(workspace: Workspace, role: WorkspaceRole) -> WorkspaceRead:
    return WorkspaceRead(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        role=role,
        permissions=sorted(permissions_for(role)),
    )


def membership_read(membership: Membership) -> WorkspaceRead:
    return workspace_read(membership.workspace, membership.role)


def member_read(member: WorkspaceMember) -> MemberRead:
    """Needs `member.user` loaded."""
    return MemberRead(
        id=member.id,
        user_id=member.user_id,
        email=member.user.email,
        role=member.role,
        created_at=member.created_at,
    )


def invite_read(invite: WorkspaceInvite) -> InviteRead:
    """Needs `invite.invited_by` loaded."""
    return InviteRead(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        invited_by=invite.invited_by.email if invite.invited_by else None,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
    )
