from datetime import timedelta

from fastapi import APIRouter, Depends

from alloy_api.auth.deps import CurrentUserDep
from alloy_api.db.session import SessionDep
from alloy_api.integrations.ratelimit import TOKEN_PER_IP, Limit, LimiterDep, per_ip
from alloy_api.workspaces import service
from alloy_api.workspaces.schemas import InvitePreview, WorkspaceRead

router = APIRouter(prefix="/invites", tags=["invites"])

INVITE_ACCEPT_PER_USER = Limit("invite-accept:user", 10, timedelta(minutes=1))


@router.get("/{token}", dependencies=[Depends(per_ip(TOKEN_PER_IP))])
async def read_invite(token: str, session: SessionDep) -> InvitePreview:
    """No login needed: the page shows who invited you where before you sign up.
    404 for an unknown, revoked, or used token; 410 for an expired one."""
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
    token: str, session: SessionDep, user: CurrentUserDep, limiter: LimiterDep
) -> WorkspaceRead:
    """Take the seat. The logged-in account's email must be the invited one.

    The token reached the invitee's inbox, so accepting also proves the account
    owns that address: an unverified account is marked verified here.
    """
    await limiter.hit(INVITE_ACCEPT_PER_USER, str(user.id))
    invite = await service.get_invite_by_token(session, token)
    member = await service.accept_invite(session, invite, user)
    return service.workspace_read(invite.workspace, member.role)
