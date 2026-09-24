from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_server.db.base import utcnow
from alloy_server.integrations.storage.cleanup import delete_stored, storage_prefix
from alloy_server.modules.auth.models import User
from alloy_server.modules.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from alloy_server.modules.workspaces.permissions import can_manage_role, permissions_for
from alloy_server.modules.workspaces.schemas import MemberResponse, WorkspaceResponse
from alloy_server.shared.exceptions import ConflictError, ForbiddenError, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.modules.workspaces.dependencies import Membership

WITH_USER = selectinload(WorkspaceMember.user)


# --- Read models -------------------------------------------------------------------


def workspace_read(workspace: Workspace, role: WorkspaceRole) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        onboarded_at=workspace.onboarded_at,
        role=role,
        permissions=sorted(permissions_for(role)),
    )


def membership_read(membership: Membership) -> WorkspaceResponse:
    return workspace_read(membership.workspace, membership.role)


def member_read(member: WorkspaceMember) -> MemberResponse:
    """Needs `member.user` loaded."""
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member.user.email,
        role=member.role,
        created_at=member.created_at,
    )


# --- Workspaces --------------------------------------------------------------------


def workspaces_query(user: User) -> Select[tuple[WorkspaceMember]]:
    return (
        select(WorkspaceMember)
        .join(WorkspaceMember.workspace)
        .options(selectinload(WorkspaceMember.workspace))
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at, Workspace.id)
    )


def create_workspace(session: AsyncSession, name: str, owner: User) -> WorkspaceMember:
    """A new workspace with `owner` in the owner seat. Flushed, not committed."""
    workspace = Workspace(name=name)
    member = WorkspaceMember(workspace=workspace, user=owner, role=WorkspaceRole.OWNER)
    session.add_all([workspace, member])
    return member


async def complete_onboarding(session: AsyncSession, workspace: Workspace) -> Workspace:
    """Idempotent. Commits."""
    if workspace.onboarded_at is None:
        workspace.onboarded_at = utcnow()
    await session.commit()
    return workspace


async def delete_workspace(session: AsyncSession, store: ObjectStore, workspace: Workspace) -> None:
    """Members, invitations, every CRM record, and every stored file go with it.
    Commits."""
    prefix = storage_prefix(workspace.id)
    await session.delete(workspace)
    await session.commit()
    await delete_stored(store, prefixes=[prefix])


# --- Members -----------------------------------------------------------------------


async def lock_workspace(session: AsyncSession, workspace_id: UUID) -> None:
    """Row-lock the workspace until the transaction ends. Every change that could
    remove an owner takes it first, so two of them cannot both count the same
    owners and both go through."""
    await session.execute(
        select(Workspace.id).where(Workspace.id == workspace_id).with_for_update()
    )


async def count_owners(session: AsyncSession, workspace_id: UUID) -> int:
    """Owners not scheduled for deletion: the purge job will take that seat, so it
    must not be the one keeping the workspace afloat."""
    return (
        await session.scalar(
            select(func.count(WorkspaceMember.id))
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .where(WorkspaceMember.role == WorkspaceRole.OWNER)
            .where(User.deleted_at.is_(None))
        )
        or 0
    )


async def ensure_not_last_owner(session: AsyncSession, member: WorkspaceMember) -> None:
    """Removing or demoting `member` must leave at least one owner."""
    if member.role is not WorkspaceRole.OWNER:
        return
    await lock_workspace(session, member.workspace_id)
    if await count_owners(session, member.workspace_id) <= 1:
        raise ConflictError("A workspace needs at least one owner")


def members_query(membership: Membership) -> Select[tuple[WorkspaceMember]]:
    return (
        select(WorkspaceMember)
        .options(WITH_USER)
        .where(WorkspaceMember.workspace_id == membership.workspace.id)
        .order_by(WorkspaceMember.created_at, WorkspaceMember.id)
    )


async def get_member(
    session: AsyncSession, membership: Membership, member_id: UUID
) -> WorkspaceMember:
    member = await session.scalar(
        select(WorkspaceMember)
        .options(WITH_USER)
        .where(WorkspaceMember.id == member_id)
        .where(WorkspaceMember.workspace_id == membership.workspace.id)
    )
    if member is None:
        raise NotFoundError("Member not found")
    return member


def role_forbidden() -> ForbiddenError:
    return ForbiddenError("Your role cannot manage that role")


async def change_role(
    session: AsyncSession, membership: Membership, member: WorkspaceMember, role: WorkspaceRole
) -> WorkspaceMember:
    """The caller must outrank both the current and the new role (owners outrank
    everyone), and the last owner cannot be demoted. Commits."""
    if not (
        can_manage_role(membership.role, member.role) and can_manage_role(membership.role, role)
    ):
        raise role_forbidden()
    if role is not WorkspaceRole.OWNER:
        await ensure_not_last_owner(session, member)
    member.role = role
    await session.commit()
    return member


async def remove_member(
    session: AsyncSession, membership: Membership, member: WorkspaceMember
) -> None:
    """Remove someone else's seat; `leave` is for the caller's own. Commits."""
    if member.id == membership.member.id:
        raise ConflictError("Use leave to remove yourself")
    if not can_manage_role(membership.role, member.role):
        raise role_forbidden()
    await ensure_not_last_owner(session, member)
    await session.delete(member)
    await session.commit()


async def leave(session: AsyncSession, membership: Membership) -> None:
    """Give up the caller's seat. The last owner cannot leave. Commits."""
    await ensure_not_last_owner(session, membership.member)
    await session.delete(membership.member)
    await session.commit()
