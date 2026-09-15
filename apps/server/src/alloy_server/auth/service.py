from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from alloy_server.auth.emails import (
    account_deletion_email,
    email_change_email,
    email_changed_notice,
    password_reset_email,
    verification_email,
)
from alloy_server.auth.models import User, UserSession
from alloy_server.auth.passwords import hash_password
from alloy_server.auth.tokens import hash_token, new_token
from alloy_server.core.exceptions import AppError, ConflictError, GoneError, NotFoundError
from alloy_server.db.base import utcnow
from alloy_server.jobs.emails import queue_email
from alloy_server.workspaces.models import (
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from alloy_server.workspaces.service import get_invite_by_token

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.config import Settings


# --- Lookups -----------------------------------------------------------------------


async def user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def email_taken(session: AsyncSession, email: str) -> bool:
    return await session.scalar(select(User.id).where(User.email == email).limit(1)) is not None


async def invite_addressed_to(session: AsyncSession, token: str | None, email: str) -> bool:
    """Whether `token` is a pending invitation for `email`. A bad token is not an
    error: the signup goes ahead and gets a verification email."""
    if token is None:
        return False
    try:
        invite = await get_invite_by_token(session, token)
    except AppError:
        return False
    return invite.email == email


async def workspaces_needing_an_owner(session: AsyncSession, user: User) -> list[str]:
    """Names of the workspaces `user` is the only owner of that have other members:
    deleting the account would leave nobody able to manage them.

    Locks every workspace the user owns until the transaction ends, the same lock
    the member routes take, so a demotion running at the same time cannot slip
    past this check.
    """
    await session.execute(
        select(Workspace.id)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .where(WorkspaceMember.role == WorkspaceRole.OWNER)
        .with_for_update(of=Workspace)
    )
    other = aliased(WorkspaceMember)
    others = (
        select(func.count(other.id))
        .where(other.workspace_id == Workspace.id)
        .where(other.user_id != user.id)
        .correlate(Workspace)
        .scalar_subquery()
    )
    other_owners = (
        select(func.count(other.id))
        .join(User, User.id == other.user_id)
        .where(other.workspace_id == Workspace.id)
        .where(other.user_id != user.id)
        .where(other.role == WorkspaceRole.OWNER)
        .where(User.deleted_at.is_(None))
        .correlate(Workspace)
        .scalar_subquery()
    )
    names = await session.scalars(
        select(Workspace.name)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .where(WorkspaceMember.role == WorkspaceRole.OWNER)
        .where(others > 0)
        .where(other_owners == 0)
        .order_by(Workspace.name)
    )
    return list(names)


# --- Accounts and sessions ---------------------------------------------------------


async def create_account(session: AsyncSession, email: str, password: str, name: str) -> User:
    """Flushed, not committed. `ConflictError` when the address is registered."""
    user = User(email=email, name=name, password_hash=await hash_password(password))
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        raise ConflictError("Email already registered") from None
    return user


async def start_session(session: AsyncSession, settings: Settings, user: User) -> str:
    """Create a session row and return its token, for the cookie. Logging in is how
    a deletion is undone, so a pending one is cleared here. Commits."""
    token = new_token()
    now = utcnow()
    user.deleted_at = None
    session.add(
        UserSession(
            user=user,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + settings.session_ttl,
        )
    )
    await session.commit()
    return token


async def revoke_sessions(session: AsyncSession, user_id: UUID, *, keep: UUID | None) -> None:
    """Log the user out everywhere, except `keep`. Commits."""
    await revoke_sessions_pending(session, user_id, keep=keep)
    await session.commit()


async def revoke_sessions_pending(
    session: AsyncSession, user_id: UUID, *, keep: UUID | None
) -> None:
    """`revoke_sessions` without the commit, for a caller with more to do."""
    statement = (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    if keep is not None:
        statement = statement.where(UserSession.id != keep)
    await session.execute(statement)


async def change_password(
    session: AsyncSession, user: User, new_password: str, *, keep: UUID
) -> None:
    """Set a new password and revoke every other session. Commits."""
    user.password_hash = await hash_password(new_password)
    # A reset link that was asked for earlier must not undo this change.
    clear_password_reset(user)
    await revoke_sessions(session, user.id, keep=keep)


async def schedule_deletion(session: AsyncSession, settings: Settings, user: User) -> None:
    """Stamp the account for the purge job, log out everywhere, and say so by email.
    Commits. `ConflictError` while the user is the only owner of a shared workspace."""
    stranded = await workspaces_needing_an_owner(session, user)
    if stranded:
        raise ConflictError(
            "You are the only owner of: " + ", ".join(stranded) + ". Make someone else an "
            "owner, or delete the workspace, before deleting your account."
        )
    user.deleted_at = utcnow()
    clear_email_change(user)
    clear_password_reset(user)
    await revoke_sessions_pending(session, user.id, keep=None)
    await queue_email(
        session,
        account_deletion_email(user, str(settings.frontend_url), settings.account_deletion_grace),
    )
    await session.commit()


# --- Email verification ------------------------------------------------------------


async def send_verification(session: AsyncSession, settings: Settings, user: User) -> None:
    """Issue a fresh verification token, replacing any pending one, and queue the
    email. Commits."""
    token = new_token()
    user.verification_token_hash = hash_token(token)
    user.verification_sent_at = utcnow()
    await queue_email(
        session,
        verification_email(user, token, str(settings.frontend_url), settings.verification_ttl),
    )
    await session.commit()


def mark_verified(user: User) -> None:
    user.email_verified_at = utcnow()
    user.verification_token_hash = None
    user.verification_sent_at = None


async def verify_email(session: AsyncSession, settings: Settings, token: str) -> User:
    """Spend a verification link. `NotFoundError` for an unknown or used token,
    `GoneError` for an expired one. Commits."""
    user = await session.scalar(
        select(User).where(User.verification_token_hash == hash_token(token))
    )
    if user is None:
        raise NotFoundError("Verification link not found")
    sent_at = user.verification_sent_at
    if sent_at is None or sent_at + settings.verification_ttl <= utcnow():
        raise GoneError("Verification link has expired")
    mark_verified(user)
    await session.commit()
    return user


# --- Password reset ----------------------------------------------------------------


async def send_password_reset(session: AsyncSession, settings: Settings, user: User) -> None:
    """Issue a fresh reset token, replacing any pending one, and queue the email.
    Commits."""
    token = new_token()
    user.password_reset_token_hash = hash_token(token)
    user.password_reset_sent_at = utcnow()
    await queue_email(
        session,
        password_reset_email(user, token, str(settings.frontend_url), settings.password_reset_ttl),
    )
    await session.commit()


def clear_password_reset(user: User) -> None:
    user.password_reset_token_hash = None
    user.password_reset_sent_at = None


async def reset_password(
    session: AsyncSession, settings: Settings, token: str, new_password: str
) -> User:
    """Spend a reset link: set the password and revoke every session. Following the
    link proves the address, so it also counts as verification. `NotFoundError`
    for an unknown or used token, `GoneError` for an expired one. Commits."""
    user = await session.scalar(
        select(User).where(User.password_reset_token_hash == hash_token(token))
    )
    if user is None:
        raise NotFoundError("Reset link not found")
    sent_at = user.password_reset_sent_at
    if sent_at is None or sent_at + settings.password_reset_ttl <= utcnow():
        raise GoneError("Reset link has expired")
    user.password_hash = await hash_password(new_password)
    clear_password_reset(user)
    if not user.email_verified:
        mark_verified(user)
    await revoke_sessions(session, user.id, keep=None)
    return user


# --- Email change ------------------------------------------------------------------


async def request_email_change(
    session: AsyncSession, settings: Settings, user: User, new_email: str
) -> None:
    """Store the new address as pending and email it a confirmation link. Commits.
    `ConflictError` if the address is taken or unchanged."""
    if new_email == user.email:
        raise ConflictError("That is already your email")
    if await email_taken(session, new_email):
        raise ConflictError("Email already registered")
    token = new_token()
    user.pending_email = new_email
    user.email_change_token_hash = hash_token(token)
    user.email_change_sent_at = utcnow()
    await queue_email(
        session,
        email_change_email(new_email, token, str(settings.frontend_url), settings.email_change_ttl),
    )
    await session.commit()


def clear_email_change(user: User) -> None:
    user.pending_email = None
    user.email_change_token_hash = None
    user.email_change_sent_at = None


async def confirm_email_change(session: AsyncSession, settings: Settings, token: str) -> User:
    """Spend a confirmation link: move the account to the pending address, which
    counts as verified, and tell the old address. `NotFoundError` for an unknown
    or used token, `GoneError` for an expired one, `ConflictError` if the address
    was registered meanwhile. Commits."""
    user = await session.scalar(
        select(User).where(User.email_change_token_hash == hash_token(token))
    )
    if user is None or user.pending_email is None:
        raise NotFoundError("Confirmation link not found")
    sent_at = user.email_change_sent_at
    if sent_at is None or sent_at + settings.email_change_ttl <= utcnow():
        raise GoneError("Confirmation link has expired")
    old_email, new_email = user.email, user.pending_email
    if await email_taken(session, new_email):
        raise ConflictError("Email already registered")
    user.email = new_email
    mark_verified(user)
    clear_email_change(user)
    try:
        # Queueing flushes, which is where the unique index would object.
        await queue_email(session, email_changed_notice(old_email, new_email))
    except IntegrityError:
        # Registered between the check above and here.
        raise ConflictError("Email already registered") from None
    await session.commit()
    return user
