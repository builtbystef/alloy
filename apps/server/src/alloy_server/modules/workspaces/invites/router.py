from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from alloy_server.db.session import SessionDep
from alloy_server.integrations.rate_limit import TOKEN_PER_IP, Limit, RateLimiterDep, per_ip
from alloy_server.modules.auth.dependencies import CurrentUserDep, VerifiedUserDep
from alloy_server.modules.workspaces.invites import service
from alloy_server.modules.workspaces.invites.schemas import InvitePreview, PendingInviteResponse
from alloy_server.modules.workspaces.schemas import WorkspaceResponse
from alloy_server.modules.workspaces.service import workspace_read

router = APIRouter(prefix="/invites", tags=["invites"])

INVITE_ACCEPT_PER_USER = Limit("invite-accept:user", 10, timedelta(minutes=1))


# --- By id: the caller's own pending invitations ------------------------------------
#
# Before the token routes, or `/pending` would be read as a token. Verified users
# only: the emailed token proves the inbox is the caller's, an id does not.


@router.get("/pending")
async def list_pending_invites(
    session: SessionDep, user: VerifiedUserDep
) -> list[PendingInviteResponse]:
    """Oldest first."""
    invites = await session.scalars(service.pending_invites_for(user.email))
    return [service.pending_invite_read(i) for i in invites]


@router.post("/pending/{invite_id}/accept")
async def accept_pending_invite(
    invite_id: UUID, session: SessionDep, user: VerifiedUserDep, limiter: RateLimiterDep
) -> WorkspaceResponse:
    """404 unless pending and addressed to the caller."""
    await limiter.hit(INVITE_ACCEPT_PER_USER, str(user.id))
    invite = await service.get_pending_invite_for(session, user, invite_id)
    member = await service.accept_invite(session, invite, user)
    return workspace_read(invite.workspace, member.role)


@router.post("/pending/{invite_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_pending_invite(
    invite_id: UUID, session: SessionDep, user: VerifiedUserDep
) -> Response:
    """The link stops working; the workspace's admins see the refusal."""
    invite = await service.get_pending_invite_for(session, user, invite_id)
    await service.decline_invite(session, invite)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- By token: the emailed link ----------------------------------------------------


@router.get("/{token}", dependencies=[Depends(per_ip(TOKEN_PER_IP))])
async def read_invite(token: str, session: SessionDep) -> InvitePreview:
    """No login needed: the page shows who invited you where before you sign up.
    404 for an unknown, revoked, declined, or used token; 410 for an expired one."""
    invite = await service.get_invite_by_token(session, token)
    return InvitePreview(
        workspace_name=invite.workspace.name,
        email=invite.email,
        role=invite.role,
        invited_by=invite.invited_by.email if invite.invited_by else None,
        expires_at=invite.expires_at,
    )


@router.post("/{token}/accept")
async def accept_invite(
    token: str, session: SessionDep, user: CurrentUserDep, limiter: RateLimiterDep
) -> WorkspaceResponse:
    """Take the seat. The logged-in account's email must be the invited one.

    The token reached the invitee's inbox, so accepting also proves the account
    owns that address: an unverified account is marked verified here.
    """
    await limiter.hit(INVITE_ACCEPT_PER_USER, str(user.id))
    invite = await service.get_invite_by_token(session, token)
    member = await service.accept_invite(session, invite, user)
    return workspace_read(invite.workspace, member.role)
