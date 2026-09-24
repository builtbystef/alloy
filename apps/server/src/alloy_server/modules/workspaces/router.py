from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Response, status

from alloy_server.config import SettingsDep
from alloy_server.db.session import SessionDep
from alloy_server.integrations.ratelimit import Limit, LimiterDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.modules.auth.dependencies import VerifiedUserDep
from alloy_server.modules.workspaces import service
from alloy_server.modules.workspaces.dependencies import (
    CanDeleteWorkspace,
    CanManageMembers,
    CanManageWorkspace,
    CanReadMembers,
    CurrentMembership,
)
from alloy_server.modules.workspaces.invites import service as invite_service
from alloy_server.modules.workspaces.invites.schemas import InviteCreate, InviteResponse
from alloy_server.modules.workspaces.schemas import (
    MemberResponse,
    MemberUpdate,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
# Routes about one workspace. Split from `router` so their paths do not repeat the
# parameter; `{workspace_id}` is consumed by the membership dependency.
scoped = APIRouter(prefix="/{workspace_id}")

INVITE_SEND_PER_USER = Limit("invite-send:user", 20, timedelta(hours=1))


@router.get("/")
async def list_workspaces(session: SessionDep, user: VerifiedUserDep) -> list[WorkspaceResponse]:
    """Every workspace the caller belongs to, oldest first."""
    members = await session.scalars(service.workspaces_query(user))
    return [service.workspace_read(m.workspace, m.role) for m in members]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate, session: SessionDep, user: VerifiedUserDep
) -> WorkspaceResponse:
    """The caller becomes its owner. Starts in onboarding; see `/onboarding/complete`."""
    member = service.create_workspace(session, body.name, user)
    await session.commit()
    return service.workspace_read(member.workspace, member.role)


@scoped.get("")
async def read_workspace(membership: CurrentMembership) -> WorkspaceResponse:
    return service.membership_read(membership)


@scoped.patch("")
async def update_workspace(
    body: WorkspaceUpdate, membership: CanManageWorkspace, session: SessionDep
) -> WorkspaceResponse:
    membership.workspace.name = body.name
    await session.commit()
    return service.membership_read(membership)


@scoped.post("/onboarding/complete")
async def complete_onboarding(
    membership: CanManageWorkspace, session: SessionDep
) -> WorkspaceResponse:
    """Sets `onboarded_at`. Idempotent."""
    await service.complete_onboarding(session, membership.workspace)
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
async def list_members(membership: CanReadMembers, session: SessionDep) -> list[MemberResponse]:
    """Longest-standing first."""
    members = await session.scalars(service.members_query(membership))
    return [service.member_read(m) for m in members]


@scoped.patch("/members/{member_id}")
async def update_member(
    member_id: UUID, body: MemberUpdate, membership: CanManageMembers, session: SessionDep
) -> MemberResponse:
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
async def list_invites(membership: CanManageMembers, session: SessionDep) -> list[InviteResponse]:
    """Pending and declined (`declined_at` set); not accepted, revoked, or expired."""
    invites = await session.scalars(invite_service.invites_query(membership))
    return [invite_service.invite_read(i) for i in invites]


@scoped.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreate,
    membership: CanManageMembers,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> InviteResponse:
    """Email a link that grants `role`. One pending invitation per address; 409 if the
    address is already a member or already invited."""
    await limiter.hit(INVITE_SEND_PER_USER, str(membership.user.id))
    invite = await invite_service.create_invite(
        session, settings, membership, body.email.lower(), body.role
    )
    return invite_service.invite_read(invite)


@scoped.post("/invites/{invite_id}/resend")
async def resend_invite(
    invite_id: UUID,
    membership: CanManageMembers,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> InviteResponse:
    """Email the invitation again with a fresh link; the previous one stops working
    and the expiry starts over. Counts against the same limit as sending one."""
    invite = await invite_service.get_pending_invite(session, membership, invite_id)
    await limiter.hit(INVITE_SEND_PER_USER, str(membership.user.id))
    await invite_service.resend_invite(session, settings, invite)
    return invite_service.invite_read(invite)


@scoped.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: UUID, membership: CanManageMembers, session: SessionDep
) -> Response:
    """The link stops working; a declined invitation leaves the list."""
    invite = await invite_service.get_pending_invite(session, membership, invite_id, declined=True)
    await invite_service.revoke_invite(session, invite)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(scoped)
