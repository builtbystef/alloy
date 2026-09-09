import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import Result, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from taskiq import TaskiqDepends

from alloy_api.auth.models import User, UserSession
from alloy_api.config import Settings
from alloy_api.crm.models import Attachment, Import, ImportStatus
from alloy_api.jobs.broker import broker
from alloy_api.jobs.deps import get_object_store, get_session, get_settings
from alloy_api.models import utcnow
from alloy_api.storage import ObjectStore
from alloy_api.storage.cleanup import delete_stored, storage_prefix
from alloy_api.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember

if TYPE_CHECKING:
    from sqlalchemy import CursorResult

logger = logging.getLogger(__name__)


def affected(result: Result[Any]) -> int:
    """Rows a `DELETE` or `UPDATE` touched. `execute` is typed as a plain `Result`."""
    return cast("CursorResult[Any]", result).rowcount


@dataclass(slots=True)
class PurgeReport:
    """How many rows each step removed."""

    sessions: int = 0
    invites: int = 0
    verification_tokens: int = 0
    password_reset_tokens: int = 0
    email_change_tokens: int = 0
    attachments: int = 0
    imports: int = 0
    timed_out_imports: int = 0
    accounts: int = 0
    workspaces: int = 0


async def purge(
    session: AsyncSession, store: ObjectStore, settings: Settings, now: datetime | None = None
) -> PurgeReport:
    """One pass. `now` is a parameter so tests can move the clock.

    Rows are removed in one transaction; the files they pointed at go after the
    commit, so a failure mid-way leaves stray objects rather than rows without
    files.
    """
    now = now or utcnow()
    cutoff = now - settings.purge_after
    report = PurgeReport()
    keys: list[str] = []
    prefixes: list[str] = []

    result = await session.execute(
        delete(UserSession).where(
            (UserSession.revoked_at < cutoff) | (UserSession.expires_at < cutoff)
        )
    )
    report.sessions = affected(result)

    result = await session.execute(
        delete(WorkspaceInvite).where(
            (WorkspaceInvite.accepted_at < cutoff)
            | (WorkspaceInvite.revoked_at < cutoff)
            | (WorkspaceInvite.expires_at < cutoff)
        )
    )
    report.invites = affected(result)

    result = await session.execute(
        update(User)
        .where(User.verification_token_hash.is_not(None))
        .where(User.verification_sent_at < cutoff - settings.verification_ttl)
        .values(verification_token_hash=None, verification_sent_at=None)
    )
    report.verification_tokens = affected(result)

    result = await session.execute(
        update(User)
        .where(User.password_reset_token_hash.is_not(None))
        .where(User.password_reset_sent_at < cutoff - settings.password_reset_ttl)
        .values(password_reset_token_hash=None, password_reset_sent_at=None)
    )
    report.password_reset_tokens = affected(result)

    result = await session.execute(
        update(User)
        .where(User.email_change_token_hash.is_not(None))
        .where(User.email_change_sent_at < cutoff - settings.email_change_ttl)
        .values(pending_email=None, email_change_token_hash=None, email_change_sent_at=None)
    )
    report.email_change_tokens = affected(result)

    # An upload URL outlives its row's creation by `storage_url_ttl`; after that,
    # a row still not completed will never be.
    abandoned_before = cutoff - settings.storage_url_ttl
    attachments = await session.scalars(
        select(Attachment)
        .where(Attachment.uploaded_at.is_(None))
        .where(Attachment.created_at < abandoned_before)
    )
    for attachment in attachments:
        keys.append(attachment.key)
        await session.delete(attachment)
        report.attachments += 1

    imports = await session.scalars(
        select(Import)
        .where(Import.status == ImportStatus.PENDING)
        .where(Import.created_at < abandoned_before)
    )
    for pending in imports:
        keys.append(pending.key)
        await session.delete(pending)
        report.imports += 1

    # Queued but never delivered (the API died between commit and send), or a run
    # the broker will not hand out again: the file goes, and the row says why.
    # The broker redelivers an unfinished run after ten minutes, so anything
    # older than `import_timeout` is not coming back on its own.
    stuck = await session.scalars(
        select(Import)
        .where(Import.status.in_([ImportStatus.QUEUED, ImportStatus.RUNNING]))
        .where(Import.updated_at < now - settings.import_timeout)
    )
    for record in stuck:
        keys.append(record.key)
        record.status = ImportStatus.FAILED
        record.error = "The import did not finish in time; upload the file again"
        record.finished_at = now
        report.timed_out_imports += 1

    # A workspace the user was alone in goes with the account. A seat in a shared
    # one is just dropped: the delete request already made sure it was not the
    # only owner seat.
    users = await session.scalars(
        select(User).where(User.deleted_at < now - settings.account_deletion_grace)
    )
    for user in users:
        other = aliased(WorkspaceMember)
        others = (
            select(func.count(other.id))
            .where(other.workspace_id == Workspace.id)
            .where(other.user_id != user.id)
            .correlate(Workspace)
            .scalar_subquery()
        )
        solo = await session.scalars(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user.id)
            .where(others == 0)
        )
        for workspace in solo:
            prefixes.append(storage_prefix(workspace.id))
            await session.delete(workspace)
            report.workspaces += 1
        await session.delete(user)
        report.accounts += 1

    await session.commit()
    await delete_stored(store, keys=keys, prefixes=prefixes)
    return report


@broker.task(task_name="purge.expired", schedule=[{"cron": "0 * * * *"}])
async def purge_expired(
    session: AsyncSession = TaskiqDepends(get_session),
    store: ObjectStore = TaskiqDepends(get_object_store),
    settings: Settings = TaskiqDepends(get_settings),
) -> dict[str, int]:
    report = await purge(session, store, settings)
    logger.info("Purged %s", report)
    return asdict(report)
