from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.auth.deps import CurrentUserDep
from alloy_api.auth.tokens import hash_token
from alloy_api.db import SessionDep
from alloy_api.models import utcnow
from alloy_api.workspaces.models import WorkspaceInvite, WorkspaceMember
from alloy_api.workspaces.schemas import InvitePreview, WorkspaceRead
from alloy_api.workspaces.service import workspace_read

router = APIRouter(prefix="/invites", tags=["invites"])


async def fetch_pending_invite(session: SessionDep, token: str) -> WorkspaceInvite:
    """404 for an unknown, revoked, or used token; 410 for an expired one."""
    invite = await session.scalar(
        select(WorkspaceInvite)
        .options(selectinload(WorkspaceInvite.workspace), selectinload(WorkspaceInvite.invited_by))
        .where(WorkspaceInvite.token_hash == hash_token(token))
        .where(WorkspaceInvite.revoked_at.is_(None))
        .where(WorkspaceInvite.accepted_at.is_(None))
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    if invite.expires_at <= utcnow():
        raise HTTPException(status.HTTP_410_GONE, "Invitation has expired")
    return invite


@router.get("/{token}")
async def read_invite(token: str, session: SessionDep) -> InvitePreview:
    """No login needed: the page shows who invited you where before you sign up."""
    invite = await fetch_pending_invite(session, token)
    return InvitePreview(
        workspace_name=invite.workspace.name,
        email=invite.email,
        role=invite.role,
        invited_by=invite.invited_by.email if invite.invited_by else None,
        expires_at=invite.expires_at,
    )


@router.post("/{token}/accept")
async def accept_invite(token: str, session: SessionDep, user: CurrentUserDep) -> WorkspaceRead:
    """Take the seat. The logged-in account's email must be the invited one.

    The token reached the invitee's inbox, so accepting also proves the account
    owns that address: an unverified account is marked verified here.
    """
    invite = await fetch_pending_invite(session, token)
    if user.email != invite.email:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This invitation was sent to a different email address"
        )
    if not user.email_verified:
        user.email_verified_at = utcnow()
        user.verification_token_hash = None
        user.verification_sent_at = None
    member = await session.scalar(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == invite.workspace_id)
        .where(WorkspaceMember.user_id == user.id)
    )
    if member is None:
        member = WorkspaceMember(workspace=invite.workspace, user=user, role=invite.role)
        session.add(member)
    invite.accepted_at = utcnow()
    await session.commit()
    return workspace_read(invite.workspace, member.role)
