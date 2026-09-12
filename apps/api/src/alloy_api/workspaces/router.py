from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Response, status

from alloy_api.auth.deps import VerifiedUserDep
from alloy_api.config import SettingsDep
from alloy_api.db.session import SessionDep
from alloy_api.integrations.ratelimit import Limit, LimiterDep
from alloy_api.integrations.storage import ObjectStoreDep
from alloy_api.workspaces import service
from alloy_api.workspaces.deps import (
    CanDeleteWorkspace,
    CanManageMembers,
    CanManageWorkspace,
    CanReadMembers,
    CurrentMembership,
)
from alloy_api.workspaces.schemas import (
    InviteCreate,
    InviteRead,
    MemberRead,
    MemberUpdate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
# Routes about one workspace. Split from `router` so their paths do not repeat the
# parameter; `{workspace_id}` is consumed by the membership dependency.
scoped = APIRouter(prefix="/{workspace_id}")

INVITE_SEND_PER_USER = Limit("invite-send:user", 20, timedelta(hours=1))


@router.get("/")
async def list_workspaces(session: SessionDep, user: VerifiedUserDep) -> list[WorkspaceRead]:
    """Every workspace the caller belongs to, oldest first."""
    members = await session.scalars(service.workspaces_query(user))
    return [service.workspace_read(m.workspace, m.role) for m in members]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate, session: SessionDep, user: VerifiedUserDep
) -> WorkspaceRead:
    """The caller becomes its owner."""
    member = service.create_workspace(session, body.name, user)
    await session.commit()
    return service.workspace_read(member.workspace, member.role)


@scoped.get("")
async def read_workspace(membership: CurrentMembership) -> WorkspaceRead:
    return service.membership_read(membership)


@scoped.patch("")
async def update_workspace(
    body: WorkspaceUpdate, membership: CanManageWorkspace, session: SessionDep
) -> WorkspaceRead:
    membership.workspace.name = body.name
    await session.commit()
    return service.membership_read(membership)


@scoped.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    membership: CanDeleteWorkspace, session: SessionDep, store: ObjectStoreDep
) -> Response:
    """Owners only. Members, invitations, every CRM record, and every stored file go
    with it."""
    await service.delete_workspace(session, store, membership.workspace)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@scoped.post("/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_workspace(membership: CurrentMembership, session: SessionDep) -> Response:
    """Give up the caller's seat. The last owner cannot leave; delete the workspace or
    make someone else an owner first."""
    await service.leave(session, membership)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@scoped.get("/members")
async def list_members(membership: CanReadMembers, session: SessionDep) -> list[MemberRead]:
    """Longest-standing first."""
    members = await session.scalars(service.members_query(membership))
    return [service.member_read(m) for m in members]


@scoped.patch("/members/{member_id}")
async def update_member(
    member_id: UUID, body: MemberUpdate, membership: CanManageMembers, session: SessionDep
) -> MemberRead:
    """Change a role. The caller must outrank both the current and the new role (owners
    outrank everyone), and the last owner cannot be demoted."""
    member = await service.get_member(session, membership, member_id)
    await service.change_role(session, membership, member, body.role)
    return service.member_read(member)


@scoped.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: UUID, membership: CanManageMembers, session: SessionDep
) -> Response:
    """Remove someone else's seat; use `leave` for your own."""
    member = await service.get_member(session, membership, member_id)
    await service.remove_member(session, membership, member)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@scoped.get("/invites")
async def list_invites(membership: CanManageMembers, session: SessionDep) -> list[InviteRead]:
    """Pending only: accepted, revoked, and expired invitations are not listed."""
    invites = await session.scalars(service.invites_query(membership))
    return [service.invite_read(i) for i in invites]


@scoped.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreate,
    membership: CanManageMembers,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> InviteRead:
    """Email a link that grants `role`. One pending invitation per address; 409 if the
    address is already a member or already invited."""
    await limiter.hit(INVITE_SEND_PER_USER, str(membership.user.id))
    invite = await service.create_invite(
        session, settings, membership, body.email.lower(), body.role
    )
    return service.invite_read(invite)


@scoped.post("/invites/{invite_id}/resend")
async def resend_invite(
    invite_id: UUID,
    membership: CanManageMembers,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> InviteRead:
    """Email the invitation again with a fresh link; the previous one stops working
    and the expiry starts over. Counts against the same limit as sending one."""
    invite = await service.get_pending_invite(session, membership, invite_id)
    await limiter.hit(INVITE_SEND_PER_USER, str(membership.user.id))
    await service.resend_invite(session, settings, invite)
    return service.invite_read(invite)


@scoped.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: UUID, membership: CanManageMembers, session: SessionDep
) -> Response:
    """The link stops working. Only pending invitations can be revoked."""
    invite = await service.get_pending_invite(session, membership, invite_id)
    await service.revoke_invite(session, invite)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(scoped)
