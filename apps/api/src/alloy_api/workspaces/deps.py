from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.auth.deps import CurrentUserDep
from alloy_api.db import SessionDep
from alloy_api.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from alloy_api.workspaces.permissions import Permission, permissions_for

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from alloy_api.auth.models import User


def workspace_not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")


def forbidden(permission: Permission) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, f"Your role does not allow {permission}")


@dataclass(frozen=True, slots=True)
class Membership:
    """The caller's seat in the workspace named in the URL."""

    workspace: Workspace
    member: WorkspaceMember

    @property
    def user(self) -> User:
        return self.member.user

    @property
    def role(self) -> WorkspaceRole:
        return self.member.role

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.member.role)

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions


async def get_current_membership(
    workspace_id: UUID, session: SessionDep, user: CurrentUserDep
) -> Membership:
    """The caller's membership of `{workspace_id}`; 404 when there is none, so workspace
    ids leak nothing to outsiders."""
    member = await session.scalar(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.workspace), selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == workspace_id)
        .where(WorkspaceMember.user_id == user.id)
    )
    if member is None:
        raise workspace_not_found()
    return Membership(workspace=member.workspace, member=member)


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]


def require(permission: Permission) -> Callable[..., Awaitable[Membership]]:
    """A dependency that is the membership when the role has `permission`, 403 otherwise."""

    async def check(membership: CurrentMembership) -> Membership:
        if not membership.can(permission):
            raise forbidden(permission)
        return membership

    return check


# The aliases handlers use. FastAPI caches `get_current_membership` per request, so
# asking for one of these costs one query however many dependencies share it.
CanReadCrm = Annotated[Membership, Depends(require(Permission.CRM_READ))]
CanWriteCrm = Annotated[Membership, Depends(require(Permission.CRM_WRITE))]
CanReadMembers = Annotated[Membership, Depends(require(Permission.MEMBERS_READ))]
CanManageMembers = Annotated[Membership, Depends(require(Permission.MEMBERS_MANAGE))]
CanManageWorkspace = Annotated[Membership, Depends(require(Permission.WORKSPACE_MANAGE))]
CanDeleteWorkspace = Annotated[Membership, Depends(require(Permission.WORKSPACE_DELETE))]
