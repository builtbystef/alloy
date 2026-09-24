from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_server.db.base import utcnow
from alloy_server.jobs.emails import queue_email
from alloy_server.modules.auth.models import User
from alloy_server.modules.auth.tokens import hash_token, new_token
from alloy_server.modules.workspaces.invites.emails import invite_email
from alloy_server.modules.workspaces.invites.schemas import InviteResponse, PendingInviteResponse
from alloy_server.modules.workspaces.models import WorkspaceInvite, WorkspaceMember, WorkspaceRole
from alloy_server.modules.workspaces.permissions import can_manage_role
from alloy_server.modules.workspaces.service import role_forbidden
from alloy_server.shared.exceptions import ConflictError, ForbiddenError, GoneError, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.config import Settings
    from alloy_server.modules.workspaces.dependencies import Membership

WITH_INVITER = selectinload(WorkspaceInvite.invited_by)


# --- Read models -------------------------------------------------------------------


def invite_read(invite: WorkspaceInvite) -> InviteResponse:
    """Needs `invite.invited_by` loaded."""
    return InviteResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        invited_by=invite.invited_by.email if invite.invited_by else None,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        declined_at=invite.declined_at,
    )


def pending_invite_read(invite: WorkspaceInvite) -> PendingInviteResponse:
    """Needs `invite.workspace` and `invite.invited_by` loaded."""
    return PendingInviteResponse(
        id=invite.id,
        workspace_name=invite.workspace.name,
        email=invite.email,
        role=invite.role,
        invited_by=invite.invited_by.email if invite.invited_by else None,
        expires_at=invite.expires_at,
    )


# --- Invitations -------------------------------------------------------------------


def open_invites() -> Select[tuple[WorkspaceInvite]]:
    """Not accepted, not revoked, not expired: pending, or declined by the invitee."""
    return (
        select(WorkspaceInvite)
        .where(WorkspaceInvite.accepted_at.is_(None))
        .where(WorkspaceInvite.revoked_at.is_(None))
        .where(WorkspaceInvite.expires_at > utcnow())
    )


def pending_invites(workspace_id: UUID) -> Select[tuple[WorkspaceInvite]]:
    return (
        open_invites()
        .where(WorkspaceInvite.workspace_id == workspace_id)
        .where(WorkspaceInvite.declined_at.is_(None))
    )


def invites_query(membership: Membership) -> Select[tuple[WorkspaceInvite]]:
    """Pending and declined, so admins see a refusal."""
    return (
        open_invites()
        .where(WorkspaceInvite.workspace_id == membership.workspace.id)
        .options(WITH_INVITER)
        .order_by(WorkspaceInvite.created_at, WorkspaceInvite.id)
    )


def pending_invites_for(email: str) -> Select[tuple[WorkspaceInvite]]:
    """With the workspace and inviter loaded."""
    return (
        open_invites()
        .where(WorkspaceInvite.email == email)
        .where(WorkspaceInvite.declined_at.is_(None))
        .options(selectinload(WorkspaceInvite.workspace), WITH_INVITER)
        .order_by(WorkspaceInvite.created_at, WorkspaceInvite.id)
    )


async def get_pending_invite_for(
    session: AsyncSession, user: User, invite_id: UUID
) -> WorkspaceInvite:
    """`NotFoundError` for any other id, another address's included."""
    invite = await session.scalar(
        pending_invites_for(user.email).where(WorkspaceInvite.id == invite_id)
    )
    if invite is None:
        raise NotFoundError("Invitation not found")
    return invite


async def get_pending_invite(
    session: AsyncSession, membership: Membership, invite_id: UUID, *, declined: bool = False
) -> WorkspaceInvite:
    """`NotFoundError` unless pending (or declined, with `declined`); `ForbiddenError`
    unless the caller's role may manage the invited one."""
    query = open_invites().where(WorkspaceInvite.workspace_id == membership.workspace.id)
    if not declined:
        query = query.where(WorkspaceInvite.declined_at.is_(None))
    invite = await session.scalar(
        query.options(WITH_INVITER).where(WorkspaceInvite.id == invite_id)
    )
    if invite is None:
        raise NotFoundError("Invitation not found")
    if not can_manage_role(membership.role, invite.role):
        raise role_forbidden()
    return invite


async def get_invite_by_token(session: AsyncSession, token: str) -> WorkspaceInvite:
    """The pending invitation behind an emailed link, with the workspace and the
    inviter loaded. `NotFoundError` for an unknown, revoked, declined, or used
    token; `GoneError` for an expired one."""
    invite = await session.scalar(
        select(WorkspaceInvite)
        .options(selectinload(WorkspaceInvite.workspace), WITH_INVITER)
        .where(WorkspaceInvite.token_hash == hash_token(token))
        .where(WorkspaceInvite.revoked_at.is_(None))
        .where(WorkspaceInvite.declined_at.is_(None))
        .where(WorkspaceInvite.accepted_at.is_(None))
    )
    if invite is None:
        raise NotFoundError("Invitation not found")
    if invite.expires_at <= utcnow():
        raise GoneError("Invitation has expired")
    return invite


async def create_invite(
    session: AsyncSession,
    settings: Settings,
    membership: Membership,
    email: str,
    role: WorkspaceRole,
) -> WorkspaceInvite:
    """Email a link that grants `role`. One pending invitation per address;
    `ConflictError` if the address is already a member or already invited,
    `ForbiddenError` if the caller's role may not grant `role`. Commits."""
    if not can_manage_role(membership.role, role):
        raise role_forbidden()
    workspace_id = membership.workspace.id

    already_member = await session.scalar(
        select(WorkspaceMember.id)
        .join(WorkspaceMember.user)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .where(WorkspaceMember.user.has(email=email))
    )
    if already_member is not None:
        raise ConflictError("Already a member of this workspace")
    already_invited = await session.scalar(
        pending_invites(workspace_id).where(WorkspaceInvite.email == email)
    )
    if already_invited is not None:
        raise ConflictError("An invitation for this email is already pending")

    token = new_token()
    now = utcnow()
    invite = WorkspaceInvite(
        workspace=membership.workspace,
        email=email,
        role=role,
        token_hash=hash_token(token),
        invited_by=membership.user,
        created_at=now,
        expires_at=now + settings.invite_ttl,
    )
    session.add(invite)
    await queue_email(session, invite_email(invite, token, str(settings.frontend_url)))
    await session.commit()
    return invite


async def resend_invite(
    session: AsyncSession, settings: Settings, invite: WorkspaceInvite
) -> WorkspaceInvite:
    """Email the invitation again with a fresh link; the previous one stops working
    and the expiry starts over. Commits."""
    token = new_token()
    invite.token_hash = hash_token(token)
    invite.expires_at = utcnow() + settings.invite_ttl
    await queue_email(session, invite_email(invite, token, str(settings.frontend_url)))
    await session.commit()
    return invite


async def revoke_invite(session: AsyncSession, invite: WorkspaceInvite) -> None:
    """The link stops working. Commits."""
    invite.revoked_at = utcnow()
    await session.commit()


async def decline_invite(session: AsyncSession, invite: WorkspaceInvite) -> None:
    """The link stops working; the address can be invited again. Commits."""
    invite.declined_at = utcnow()
    await session.commit()


async def accept_invite(
    session: AsyncSession, invite: WorkspaceInvite, user: User
) -> WorkspaceMember:
    """Take the seat. The account's email must be the invited one. The token
    reached the invitee's inbox, so accepting also proves the account owns that
    address: an unverified account is marked verified here. Commits."""
    if user.email != invite.email:
        raise ForbiddenError("This invitation was sent to a different email address")
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
    return member
