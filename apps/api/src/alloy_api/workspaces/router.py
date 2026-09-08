from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_api.auth.deps import VerifiedUserDep
from alloy_api.auth.tokens import hash_token, new_token
from alloy_api.config import SettingsDep
from alloy_api.db import SessionDep
from alloy_api.jobs.emails import send_email
from alloy_api.models import utcnow
from alloy_api.storage import ObjectStoreDep
from alloy_api.workspaces.deps import (
    CanDeleteWorkspace,
    CanManageMembers,
    CanManageWorkspace,
    CanReadMembers,
    CurrentMembership,
)
from alloy_api.workspaces.emails import invite_email
from alloy_api.workspaces.models import (
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
    WorkspaceRole,
)
from alloy_api.workspaces.permissions import can_manage_role
from alloy_api.workspaces.schemas import (
    InviteCreate,
    InviteRead,
    MemberRead,
    MemberUpdate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from alloy_api.workspaces.service import (
    create_workspace,
    invite_read,
    member_read,
    membership_read,
    workspace_read,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.workspaces.deps import Membership

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
# Routes about one workspace. Split from `router` so their paths do not repeat the
# parameter; `{workspace_id}` is consumed by the membership dependency.
scoped = APIRouter(prefix="/{workspace_id}")

WITH_USER = selectinload(WorkspaceMember.user)
WITH_INVITER = selectinload(WorkspaceInvite.invited_by)


def role_forbidden() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot manage that role")


async def count_owners(session: AsyncSession, workspace_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count(WorkspaceMember.id))
            .where(WorkspaceMember.workspace_id == workspace_id)
            .where(WorkspaceMember.role == WorkspaceRole.OWNER)
        )
        or 0
    )


async def ensure_not_last_owner(session: AsyncSession, member: WorkspaceMember) -> None:
    """Removing or demoting `member` must leave at least one owner."""
    if member.role is WorkspaceRole.OWNER and await count_owners(session, member.workspace_id) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "A workspace needs at least one owner")


def pending_invites(workspace_id: UUID):  # noqa: ANN201 - a Select[tuple[WorkspaceInvite]]
    return (
        select(WorkspaceInvite)
        .where(WorkspaceInvite.workspace_id == workspace_id)
        .where(WorkspaceInvite.accepted_at.is_(None))
        .where(WorkspaceInvite.revoked_at.is_(None))
        .where(WorkspaceInvite.expires_at > utcnow())
    )


@router.get("/")
async def list_workspaces(session: SessionDep, user: VerifiedUserDep) -> list[WorkspaceRead]:
    """Every workspace the caller belongs to, oldest first."""
    members = await session.scalars(
        select(WorkspaceMember)
        .join(WorkspaceMember.workspace)
        .options(selectinload(WorkspaceMember.workspace))
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at, Workspace.id)
    )
    return [workspace_read(m.workspace, m.role) for m in members]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_workspace_route(
    body: WorkspaceCreate, session: SessionDep, user: VerifiedUserDep
) -> WorkspaceRead:
    """The caller becomes its owner."""
    member = create_workspace(session, body.name, user)
    await session.commit()
    return workspace_read(member.workspace, member.role)


@scoped.get("")
async def read_workspace(membership: CurrentMembership) -> WorkspaceRead:
    return membership_read(membership)


@scoped.patch("")
async def update_workspace(
    body: WorkspaceUpdate, membership: CanManageWorkspace, session: SessionDep
) -> WorkspaceRead:
    membership.workspace.name = body.name
    await session.commit()
    return membership_read(membership)


@scoped.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    membership: CanDeleteWorkspace, session: SessionDep, store: ObjectStoreDep
) -> Response:
    """Owners only. Members, invitations, every CRM record, and every stored file go
    with it."""
    await store.delete_prefix(f"workspaces/{membership.workspace.id}/")
    await session.delete(membership.workspace)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@scoped.post("/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_workspace(membership: CurrentMembership, session: SessionDep) -> Response:
    """Give up the caller's seat. The last owner cannot leave; delete the workspace or
    make someone else an owner first."""
    await ensure_not_last_owner(session, membership.member)
    await session.delete(membership.member)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def fetch_member(
    session: AsyncSession, membership: Membership, member_id: UUID
) -> WorkspaceMember:
    member = await session.scalar(
        select(WorkspaceMember)
        .options(WITH_USER)
        .where(WorkspaceMember.id == member_id)
        .where(WorkspaceMember.workspace_id == membership.workspace.id)
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return member


@scoped.get("/members")
async def list_members(membership: CanReadMembers, session: SessionDep) -> list[MemberRead]:
    """Longest-standing first."""
    members = await session.scalars(
        select(WorkspaceMember)
        .options(WITH_USER)
        .where(WorkspaceMember.workspace_id == membership.workspace.id)
        .order_by(WorkspaceMember.created_at, WorkspaceMember.id)
    )
    return [member_read(m) for m in members]


@scoped.patch("/members/{member_id}")
async def update_member(
    member_id: UUID, body: MemberUpdate, membership: CanManageMembers, session: SessionDep
) -> MemberRead:
    """Change a role. The caller must outrank both the current and the new role (owners
    outrank everyone), and the last owner cannot be demoted."""
    member = await fetch_member(session, membership, member_id)
    if not (
        can_manage_role(membership.role, member.role)
        and can_manage_role(membership.role, body.role)
    ):
        raise role_forbidden()
    if body.role is not WorkspaceRole.OWNER:
        await ensure_not_last_owner(session, member)
    member.role = body.role
    await session.commit()
    return member_read(member)


@scoped.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: UUID, membership: CanManageMembers, session: SessionDep
) -> Response:
    """Remove someone else's seat; use `leave` for your own."""
    member = await fetch_member(session, membership, member_id)
    if member.id == membership.member.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Use leave to remove yourself")
    if not can_manage_role(membership.role, member.role):
        raise role_forbidden()
    await ensure_not_last_owner(session, member)
    await session.delete(member)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@scoped.get("/invites")
async def list_invites(membership: CanManageMembers, session: SessionDep) -> list[InviteRead]:
    """Pending only: accepted, revoked, and expired invitations are not listed."""
    invites = await session.scalars(
        pending_invites(membership.workspace.id)
        .options(WITH_INVITER)
        .order_by(WorkspaceInvite.created_at, WorkspaceInvite.id)
    )
    return [invite_read(i) for i in invites]


@scoped.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreate,
    membership: CanManageMembers,
    session: SessionDep,
    settings: SettingsDep,
) -> InviteRead:
    """Email a link that grants `role`. One pending invitation per address; 409 if the
    address is already a member or already invited."""
    if not can_manage_role(membership.role, body.role):
        raise role_forbidden()
    email = body.email.lower()
    workspace_id = membership.workspace.id

    already_member = await session.scalar(
        select(WorkspaceMember.id)
        .join(WorkspaceMember.user)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .where(WorkspaceMember.user.has(email=email))
    )
    if already_member is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member of this workspace")
    already_invited = await session.scalar(
        pending_invites(workspace_id).where(WorkspaceInvite.email == email)
    )
    if already_invited is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An invitation for this email is already pending"
        )

    token = new_token()
    now = utcnow()
    invite = WorkspaceInvite(
        workspace=membership.workspace,
        email=email,
        role=body.role,
        token_hash=hash_token(token),
        invited_by=membership.user,
        created_at=now,
        expires_at=now + settings.invite_ttl,
    )
    session.add(invite)
    await session.commit()
    await send_email.kiq(invite_email(invite, token, str(settings.frontend_url)))
    return invite_read(invite)


@scoped.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: UUID, membership: CanManageMembers, session: SessionDep
) -> Response:
    """The link stops working. Only pending invitations can be revoked."""
    invite = await session.scalar(
        pending_invites(membership.workspace.id).where(WorkspaceInvite.id == invite_id)
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    if not can_manage_role(membership.role, invite.role):
        raise role_forbidden()
    invite.revoked_at = utcnow()
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(scoped)
