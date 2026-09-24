"""Helpers the tool modules share: paging, row shapes, ownership checks, bulk
limits, the approval pause, and the chat's uploads."""

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic_ai import ApprovalRequired, CustomEvent, RunContext
from sqlalchemy import func, select

from alloy_server.db.base import utcnow
from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.models import ChatUpload
from alloy_server.modules.assistant.tools.registry import retry
from alloy_server.modules.assistant.tools.shapes import (
    ActivityRow,
    AttachmentRow,
    CompanyRow,
    ContactRow,
    TaskRow,
)
from alloy_server.modules.crm.attachments.models import Attachment
from alloy_server.modules.crm.companies.models import Company
from alloy_server.modules.crm.contacts.models import Activity, Contact
from alloy_server.modules.crm.tasks.models import Task
from alloy_server.modules.workspaces.permissions import Permission

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm.interfaces import ORMOption

    from alloy_server.modules.crm.models import OwnedByWorkspace

PAGE_SIZE = 20
# A bulk call may not touch more rows than this.
MAX_BULK = 100
# Rows shown on the approval card; the total says how many there are.
PREVIEW_ROWS = 25


@dataclass(kw_only=True)
class ApprovalPreviewEvent(CustomEvent):
    """What a paused tool call is about to do, for the approval card: a title and a
    few columns of rows. Sent to the browser as a `data-approval_preview` part and
    kept on the response's metadata, so a reload shows the same table. The
    `tool_call_id` is the envelope's, set by `emit` inside the tool."""

    title: str
    columns: list[str]
    rows: list[list[str]]
    total: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "title": self.title,
            "columns": self.columns,
            "rows": self.rows,
            "total": self.total,
        }


def page_bounds(page: int) -> tuple[int, int]:
    return PAGE_SIZE, (page - 1) * PAGE_SIZE


def next_page(page: int, shown: int, total: int) -> int | None:
    _, offset = page_bounds(page)
    return page + 1 if offset + shown < total else None


async def count_rows(session: AsyncSession, query: Select[Any]) -> int:
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return total or 0


def contact_row(deps: AgentDeps, contact: Contact) -> ContactRow:
    return ContactRow(
        id=contact.id,
        name=contact.name,
        email=contact.email,
        job_title=contact.job_title,
        status=contact.status,
        company=contact.company.name if contact.company else None,
        company_id=contact.company_id,
        last_contacted_at=contact.last_contacted_at,
        url=deps.record_url("contacts", contact.id),
    )


def company_row(deps: AgentDeps, company: Company) -> CompanyRow:
    return CompanyRow(
        id=company.id,
        name=company.name,
        website=company.website,
        industry=company.industry,
        url=deps.record_url("companies", company.id),
    )


def activity_row(activity: Activity) -> ActivityRow:
    return ActivityRow(
        id=activity.id,
        contact_id=activity.contact_id,
        type=activity.type,
        notes=activity.notes,
        created_at=activity.created_at,
        logged_by=activity.created_by.email if activity.created_by else None,
    )


def task_row(deps: AgentDeps, task: Task) -> TaskRow:
    company = task.linked_company
    base = str(deps.settings.frontend_url).rstrip("/")
    return TaskRow(
        id=task.id,
        title=task.title,
        status=task.status,
        due_at=task.due_at,
        contact=task.contact.name if task.contact else None,
        contact_id=task.contact_id,
        company=company.name if company else None,
        company_id=company.id if company else None,
        notes=task.notes,
        url=f"{base}/{deps.workspace_id}/tasks",
    )


def attachment_row(deps: AgentDeps, attachment: Attachment) -> AttachmentRow:
    return AttachmentRow(
        id=attachment.id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size=attachment.size,
        contact_id=attachment.contact_id,
        company_id=attachment.company_id,
        download_url=deps.download_url(attachment.id),
    )


async def owned[T: OwnedByWorkspace](
    deps: AgentDeps, model: type[T], object_id: UUID, *options: ORMOption
) -> T:
    """The row, if it is in this workspace; a retry prompt naming the id otherwise."""
    row = await deps.session.scalar(
        select(model)
        .options(*options)
        .where(model.id == object_id)
        .where(model.workspace_id == deps.workspace_id)
    )
    if row is None:
        raise retry(f"No {model.__name__.lower()} with id {object_id} in this workspace.")
    return row


async def owned_all[T: OwnedByWorkspace](
    deps: AgentDeps, model: type[T], ids: Sequence[UUID], *options: ORMOption
) -> list[T]:
    """The rows for `ids`, in the order given; a retry prompt if any is missing."""
    if not ids:
        raise retry("Pass at least one id.")
    if len(ids) > MAX_BULK:
        raise retry(f"At most {MAX_BULK} items per call; split the request.")
    rows = {
        row.id: row
        for row in await deps.session.scalars(
            select(model)
            .options(*options)
            .where(model.id.in_(ids))
            .where(model.workspace_id == deps.workspace_id)
        )
    }
    missing = [str(i) for i in ids if i not in rows]
    if missing:
        raise retry(f"No {model.__name__.lower()} with id {', '.join(missing)} in this workspace.")
    return [rows[i] for i in ids]


def check_bulk(items: Sequence[Any]) -> None:
    if not items:
        raise retry("Pass at least one item.")
    if len(items) > MAX_BULK:
        raise retry(f"At most {MAX_BULK} items per call; split the request.")


async def pause_for_approval(
    ctx: RunContext[AgentDeps], *, title: str, columns: list[str], rows: list[list[str]]
) -> None:
    """Stop here until the user approves, unless this call is the approved re-run.

    The preview goes to the browser as a data part for the approval card, and is
    kept on `deps` so the saved transcript shows the same table after a reload.
    """
    if ctx.tool_call_approved:
        return
    preview = ApprovalPreviewEvent(
        tool_call_id=ctx.tool_call_id,
        title=title,
        columns=columns,
        rows=rows[:PREVIEW_ROWS],
        total=len(rows),
    )
    ctx.deps.approval_previews[ctx.tool_call_id or ""] = preview.to_payload()
    await ctx.emit(preview)
    raise ApprovalRequired


def write_allowed(ctx: RunContext[AgentDeps]) -> None:
    """The toolset hides write tools from viewers; this is the backstop."""
    if not ctx.deps.membership.can(Permission.CRM_WRITE):
        raise retry("Your role in this workspace is read-only; you cannot change records.")


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def short(value: object, width: int = 60) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


async def chat_uploads(deps: AgentDeps, upload_ids: Sequence[UUID]) -> list[ChatUpload]:
    """Uploads the model may attach: this user's, in this conversation, uploaded, and
    not attached yet."""
    if not upload_ids:
        return []
    uploads = {
        upload.id: upload
        for upload in await deps.session.scalars(
            select(ChatUpload)
            .where(ChatUpload.id.in_(upload_ids))
            .where(ChatUpload.workspace_id == deps.workspace_id)
            .where(ChatUpload.user_id == deps.membership.user.id)
            .where(ChatUpload.conversation_id == deps.conversation_id)
        )
    }
    result: list[ChatUpload] = []
    for upload_id in upload_ids:
        upload = uploads.get(upload_id)
        if upload is None:
            raise retry(f"No file with upload id {upload_id} in this conversation.")
        if upload.uploaded_at is None:
            raise retry(f"The file {upload.filename!r} has not finished uploading.")
        if upload.attachment_id is not None:
            raise retry(f"The file {upload.filename!r} is already attached to a record.")
        result.append(upload)
    return result


def attach(deps: AgentDeps, upload: ChatUpload, parent: Contact | Company) -> Attachment:
    """An attachment on `parent` pointing at the upload's object. No bytes move."""
    attachment = Attachment(
        id=uuid.uuid7(),
        workspace_id=deps.workspace_id,
        contact_id=parent.id if isinstance(parent, Contact) else None,
        company_id=parent.id if isinstance(parent, Company) else None,
        uploaded_by_user_id=deps.membership.user.id,
        filename=upload.filename,
        content_type=upload.content_type,
        size=upload.size,
        key=upload.key,
        uploaded_at=utcnow(),
    )
    deps.session.add(attachment)
    upload.attachment = attachment
    return attachment


async def attachments_of(deps: AgentDeps, parent: Contact | Company) -> list[AttachmentRow]:
    column = Attachment.contact_id if isinstance(parent, Contact) else Attachment.company_id
    rows = await deps.session.scalars(
        select(Attachment)
        .where(column == parent.id)
        .where(Attachment.uploaded_at.is_not(None))
        .order_by(Attachment.uploaded_at.desc())
    )
    return [attachment_row(deps, a) for a in rows]
