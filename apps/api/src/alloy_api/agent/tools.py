import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import ApprovalRequired, ModelRetry, RunContext
from pydantic_ai.toolsets import FilteredToolset, FunctionToolset
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_api.agent.deps import AgentDeps, ApprovalPreviewEvent
from alloy_api.agent.models import ChatUpload
from alloy_api.crm import service
from alloy_api.crm.companies import CompanyFilters, companies_query
from alloy_api.crm.contacts import ContactFilters, contacts_query
from alloy_api.crm.dates import DueFilter
from alloy_api.crm.models import (
    Activity,
    ActivityType,
    Attachment,
    Company,
    Contact,
    ContactStatus,
    RowSource,
    Task,
    TaskStatus,
)
from alloy_api.crm.schemas import (
    ActivityCreate,
    CompanyCreate,
    CompanyUpdate,
    ContactCreate,
    ContactUpdate,
    TaskCreate,
    TaskUpdate,
)
from alloy_api.crm.tasks import TaskFilters, tasks_query
from alloy_api.models import utcnow
from alloy_api.workspaces.models import WorkspaceMember
from alloy_api.workspaces.permissions import Permission

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm.interfaces import ORMOption

    from alloy_api.crm.models import OwnedByWorkspace

PAGE_SIZE = 20
# A bulk call may not touch more rows than this.
MAX_BULK = 100
# Rows shown on the approval card; the total says how many there are.
PREVIEW_ROWS = 25

Tier = Literal["read", "write", "approval"]

toolset = FunctionToolset[AgentDeps](
    # Tools share one database session, so they must not run concurrently.
    sequential=True,
    # Strict schemas would force every optional field to be present, which turns a
    # partial update into "clear everything else".
    strict=False,
)


def _read_tool(func: Any) -> Any:  # noqa: ANN401 - the decorator keeps the function's type
    return toolset.tool(metadata={"tier": "read"})(func)


def _write_tool(func: Any) -> Any:  # noqa: ANN401
    return toolset.tool(metadata={"tier": "write"})(func)


def _approval_tool(func: Any) -> Any:  # noqa: ANN401
    return toolset.tool(metadata={"tier": "approval"})(func)


def _tool_tier(metadata: dict[str, Any] | None) -> Tier:
    tier = (metadata or {}).get("tier", "approval")
    return tier if tier in ("read", "write", "approval") else "approval"


def _visible_to(ctx: RunContext[AgentDeps], tool_def: Any) -> bool:  # noqa: ANN401
    """Viewers see read tools only, so their model never tries a write."""
    if ctx.deps.membership.can(Permission.CRM_WRITE):
        return True
    return _tool_tier(tool_def.metadata) == "read"


# What the agent registers: the tools above, filtered by the caller's permission.
permitted_toolset: FilteredToolset[AgentDeps] = FilteredToolset(toolset, _visible_to)


def retry(message: str) -> ModelRetry:
    """Tell the model what was wrong with the call so it can correct it."""
    return ModelRetry(message)


# --- Result shapes -----------------------------------------------------------------


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    next_page: int | None = Field(
        description="Pass as `page` to get more; null when this is the last."
    )


class ContactRow(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    job_title: str | None
    status: ContactStatus
    company: str | None
    company_id: uuid.UUID | None
    last_contacted_at: datetime | None
    url: str


class CompanyRow(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None
    industry: str | None
    url: str


class CompanySearchRow(CompanyRow):
    contact_count: int
    latest_contact_at: datetime | None = Field(
        description="The most recent `last_contacted_at` among the company's contacts."
    )


class ActivityRow(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    type: ActivityType
    notes: str | None
    created_at: datetime
    logged_by: str | None


class TaskRow(BaseModel):
    id: uuid.UUID
    title: str
    status: TaskStatus
    due_at: datetime | None
    contact: str | None
    contact_id: uuid.UUID | None
    company: str | None
    company_id: uuid.UUID | None
    notes: str | None
    url: str


class AttachmentRow(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    contact_id: uuid.UUID | None
    company_id: uuid.UUID | None
    download_url: str


class ContactDetail(BaseModel):
    contact: ContactRow
    phone: str | None
    recent_activities: list[ActivityRow]
    open_tasks: list[TaskRow]
    attachments: list[AttachmentRow]
    created_at: datetime


class CompanyDetail(BaseModel):
    company: CompanyRow
    notes: str | None
    contacts: list[ContactRow]
    more_contacts: int = Field(description="Contacts beyond the ones listed.")
    attachments: list[AttachmentRow]
    created_at: datetime


class CompanyGroup(BaseModel):
    company: CompanyRow | None = Field(description="Null for contacts without a company.")
    contacts: list[ContactRow]


class GroupedContacts(BaseModel):
    groups: list[CompanyGroup]
    total: int
    page: int
    next_page: int | None


class Skipped(BaseModel):
    name: str
    reason: str
    existing: ContactRow | None = None


class ContactsCreated(BaseModel):
    created: list[ContactRow]
    skipped: list[Skipped]
    attached: list[AttachmentRow]


class CompaniesCreated(BaseModel):
    created: list[CompanyRow]
    attached: list[AttachmentRow]


class Deleted(BaseModel):
    deleted: list[str] = Field(description="Names of what was removed.")


class MemberRow(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str


class WorkspaceInfo(BaseModel):
    id: uuid.UUID
    name: str
    your_role: str
    you_can_write: bool
    today: str
    time_zone: str


# --- Argument shapes ---------------------------------------------------------------


UploadIds = Annotated[
    list[uuid.UUID],
    Field(
        default_factory=list,
        description="Ids of files the user dropped into this chat, to attach to the new record.",
    ),
]


class ContactItem(ContactCreate):
    company_name: str | None = Field(
        None,
        description="Name of an existing company to link, matched case-insensitively. "
        "Prefer `company_id` when known. Create the company first if it does not exist.",
    )
    upload_ids: UploadIds
    allow_duplicate_email: bool = Field(
        default=False,
        description="Create even when a contact with the same email exists. Otherwise the "
        "item is skipped and the existing contact returned, so you can ask the user.",
    )


class CompanyItem(CompanyCreate):
    upload_ids: UploadIds


class ContactChange(BaseModel):
    contact_id: uuid.UUID
    changes: ContactUpdate = Field(
        description="Only the fields to change. A field set to null is cleared."
    )


class CompanyChange(BaseModel):
    company_id: uuid.UUID
    changes: CompanyUpdate = Field(
        description="Only the fields to change. A field set to null is cleared."
    )


class TaskChange(BaseModel):
    task_id: uuid.UUID
    changes: TaskUpdate = Field(
        description="Only the fields to change. `status: done` completes a task, "
        "`status: open` reopens it."
    )


class ActivityItem(ActivityCreate):
    contact_id: uuid.UUID


class FileTarget(BaseModel):
    upload_id: uuid.UUID = Field(description="A file the user dropped into this chat.")
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None


# --- Helpers -----------------------------------------------------------------------


def _page_bounds(page: int) -> tuple[int, int]:
    return PAGE_SIZE, (page - 1) * PAGE_SIZE


def _next_page(page: int, shown: int, total: int) -> int | None:
    _, offset = _page_bounds(page)
    return page + 1 if offset + shown < total else None


async def _count(session: AsyncSession, query: Select[Any]) -> int:
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return total or 0


def _contact_row(deps: AgentDeps, contact: Contact) -> ContactRow:
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


def _company_row(deps: AgentDeps, company: Company) -> CompanyRow:
    return CompanyRow(
        id=company.id,
        name=company.name,
        website=company.website,
        industry=company.industry,
        url=deps.record_url("companies", company.id),
    )


def _activity_row(activity: Activity) -> ActivityRow:
    return ActivityRow(
        id=activity.id,
        contact_id=activity.contact_id,
        type=activity.type,
        notes=activity.notes,
        created_at=activity.created_at,
        logged_by=activity.created_by.email if activity.created_by else None,
    )


def _task_row(deps: AgentDeps, task: Task) -> TaskRow:
    base = str(deps.settings.frontend_url).rstrip("/")
    return TaskRow(
        id=task.id,
        title=task.title,
        status=task.status,
        due_at=task.due_at,
        contact=task.contact.name if task.contact else None,
        contact_id=task.contact_id,
        company=task.company.name if task.company else None,
        company_id=task.company_id,
        notes=task.notes,
        url=f"{base}/{deps.workspace_id}/tasks",
    )


def _attachment_row(deps: AgentDeps, attachment: Attachment) -> AttachmentRow:
    return AttachmentRow(
        id=attachment.id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size=attachment.size,
        contact_id=attachment.contact_id,
        company_id=attachment.company_id,
        download_url=deps.download_url(attachment.id),
    )


async def _owned[T: OwnedByWorkspace](
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


async def _owned_all[T: OwnedByWorkspace](
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


def _check_bulk(items: Sequence[Any]) -> None:
    if not items:
        raise retry("Pass at least one item.")
    if len(items) > MAX_BULK:
        raise retry(f"At most {MAX_BULK} items per call; split the request.")


async def _pause_for_approval(
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


def _write_allowed(ctx: RunContext[AgentDeps]) -> None:
    """The toolset hides write tools from viewers; this is the backstop."""
    if not ctx.deps.membership.can(Permission.CRM_WRITE):
        raise retry("Your role in this workspace is read-only; you cannot change records.")


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _short(value: object, width: int = 60) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


async def _resolve_company(deps: AgentDeps, item: ContactItem) -> UUID | None:
    if item.company_id is not None:
        await _owned(deps, Company, item.company_id)
        return item.company_id
    if item.company_name is None:
        return None
    matches = list(
        await deps.session.scalars(
            select(Company)
            .where(Company.workspace_id == deps.workspace_id)
            .where(func.lower(Company.name) == item.company_name.strip().lower())
        )
    )
    if len(matches) == 1:
        return matches[0].id
    if not matches:
        raise retry(
            f"No company named {item.company_name!r}. Search with search_companies, create "
            "it with create_companies, or leave company_name out."
        )
    options = ", ".join(f"{m.name} ({m.id})" for m in matches)
    raise retry(
        f"Several companies are named {item.company_name!r}: {options}. Pass company_id instead."
    )


async def _duplicate_by_email(deps: AgentDeps, email: str | None) -> Contact | None:
    if email is None:
        return None
    return await deps.session.scalar(
        select(Contact)
        .options(selectinload(Contact.company))
        .where(Contact.workspace_id == deps.workspace_id)
        .where(func.lower(Contact.email) == email.lower())
        .limit(1)
    )


async def _chat_uploads(deps: AgentDeps, upload_ids: Sequence[UUID]) -> list[ChatUpload]:
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


def _attach(deps: AgentDeps, upload: ChatUpload, parent: Contact | Company) -> Attachment:
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


async def _attachments_of(deps: AgentDeps, parent: Contact | Company) -> list[AttachmentRow]:
    column = Attachment.contact_id if isinstance(parent, Contact) else Attachment.company_id
    rows = await deps.session.scalars(
        select(Attachment)
        .where(column == parent.id)
        .where(Attachment.uploaded_at.is_not(None))
        .order_by(Attachment.uploaded_at.desc())
    )
    return [_attachment_row(deps, a) for a in rows]


# --- Contacts ----------------------------------------------------------------------


@_read_tool
async def search_contacts(  # noqa: PLR0913
    ctx: RunContext[AgentDeps],
    *,
    q: str | None = None,
    status: ContactStatus | None = None,
    company_id: uuid.UUID | None = None,
    stale_days: int | None = None,
    group_by_company: bool = False,
    page: int = 1,
) -> Page[ContactRow] | GroupedContacts:
    """Find contacts. Use it to look up people by name, email, or company, and to
    answer "who have we not contacted recently" with `stale_days`.

    Args:
        q: Matches name, email, phone, job title, or company name (case-insensitive).
        status: Only contacts with this status.
        company_id: Only contacts at this company.
        stale_days: Only contacts not contacted for this many days, or never. Use 30
            unless the user gives a number; do not ask. Results come oldest-contact
            first, never-contacted first of all.
        group_by_company: Return the page grouped by company, for questions about
            which companies have not been contacted recently.
        page: 1-based page of 20.
    """
    if page < 1:
        raise retry("page starts at 1.")
    deps = ctx.deps
    filters = ContactFilters(q=q, status=status, company_id=company_id)
    query = contacts_query(deps.membership, filters)
    if stale_days is not None:
        if stale_days < 1:
            raise retry("stale_days must be at least 1.")
        stale_before = utcnow() - timedelta(days=stale_days)
        query = (
            query.order_by(None)
            .where(Contact.last_contacted_at.is_(None) | (Contact.last_contacted_at < stale_before))
            .order_by(Contact.last_contacted_at.asc().nulls_first(), Contact.name, Contact.id)
        )
    total = await _count(deps.session, query)
    limit, offset = _page_bounds(page)
    contacts = list(await deps.session.scalars(query.limit(limit).offset(offset)))
    rows = [_contact_row(deps, c) for c in contacts]
    if not group_by_company:
        return Page(
            items=rows, total=total, page=page, next_page=_next_page(page, len(rows), total)
        )
    groups: dict[UUID | None, CompanyGroup] = {}
    for contact, row in zip(contacts, rows, strict=True):
        group = groups.get(contact.company_id)
        if group is None:
            company = _company_row(deps, contact.company) if contact.company else None
            group = groups[contact.company_id] = CompanyGroup(company=company, contacts=[])
        group.contacts.append(row)
    return GroupedContacts(
        groups=list(groups.values()),
        total=total,
        page=page,
        next_page=_next_page(page, len(rows), total),
    )


@_read_tool
async def get_contact(ctx: RunContext[AgentDeps], contact_id: uuid.UUID) -> ContactDetail:
    """Everything about one contact: details, the five most recent activities, open
    tasks, and attached files."""
    deps = ctx.deps
    contact = await _owned(deps, Contact, contact_id, selectinload(Contact.company))
    activities = await deps.session.scalars(
        select(Activity)
        .where(Activity.contact_id == contact.id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(5)
    )
    tasks = await deps.session.scalars(
        select(Task)
        .options(selectinload(Task.contact), selectinload(Task.company))
        .where(Task.contact_id == contact.id, Task.status == TaskStatus.OPEN)
        .order_by(Task.due_at.asc().nulls_last(), Task.id)
    )
    return ContactDetail(
        contact=_contact_row(deps, contact),
        phone=contact.phone,
        recent_activities=[_activity_row(a) for a in activities],
        open_tasks=[_task_row(deps, t) for t in tasks],
        attachments=await _attachments_of(deps, contact),
        created_at=contact.created_at,
    )


@_write_tool
async def create_contacts(ctx: RunContext[AgentDeps], items: list[ContactItem]) -> ContactsCreated:
    """Create contacts. One item runs at once; more than one pauses for the user's
    approval. An item whose email already belongs to a contact is skipped and the
    existing contact returned, unless `allow_duplicate_email` is set. Files from the
    chat can be attached with `upload_ids`."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    company_ids = [await _resolve_company(deps, item) for item in items]
    for item in items:
        await _chat_uploads(deps, item.upload_ids)
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Create {_plural(len(items), 'contact')}",
            columns=["Name", "Email", "Company"],
            rows=[[item.name, item.email or "", item.company_name or ""] for item in items],
        )
    result = ContactsCreated(created=[], skipped=[], attached=[])
    for item, company_id in zip(items, company_ids, strict=True):
        existing = (
            None if item.allow_duplicate_email else await _duplicate_by_email(deps, item.email)
        )
        if existing is not None:
            result.skipped.append(
                Skipped(
                    name=item.name,
                    reason=f"A contact with the email {item.email} already exists.",
                    existing=_contact_row(deps, existing),
                )
            )
            continue
        body = ContactCreate(**item.model_dump(include=set(ContactCreate.model_fields)))
        body.company_id = company_id
        contact = await service.create_contact(
            deps.session, deps.membership, body, source=RowSource.AGENT
        )
        for upload in await _chat_uploads(deps, item.upload_ids):
            result.attached.append(_attachment_row(deps, _attach(deps, upload, contact)))
        await deps.session.flush()
        await deps.session.refresh(contact, ["company"])
        result.created.append(_contact_row(deps, contact))
    await deps.session.commit()
    return result


@_write_tool
async def update_contacts(
    ctx: RunContext[AgentDeps], items: list[ContactChange]
) -> list[ContactRow]:
    """Change contacts: name, email, phone, job title, company, status, or last
    contacted date. One item runs at once; more than one pauses for approval."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    contacts = await _owned_all(deps, Contact, [item.contact_id for item in items])
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Update {_plural(len(items), 'contact')}",
            columns=["Contact", "Changes"],
            rows=[
                [contact.name, _short(item.changes.model_dump(exclude_unset=True), 80)]
                for contact, item in zip(contacts, items, strict=True)
            ],
        )
    updated = [
        await service.update_contact(deps.session, deps.membership, item.contact_id, item.changes)
        for item in items
    ]
    await deps.session.commit()
    for contact in updated:
        await deps.session.refresh(contact, ["company"])
    return [_contact_row(deps, c) for c in updated]


@_approval_tool
async def delete_contacts(ctx: RunContext[AgentDeps], contact_ids: list[uuid.UUID]) -> Deleted:
    """Delete contacts, with their activities and attached files. Tasks linked to them
    are kept. Always pauses for the user's approval."""
    _write_allowed(ctx)
    deps = ctx.deps
    contacts = await _owned_all(deps, Contact, contact_ids, selectinload(Contact.company))
    await _pause_for_approval(
        ctx,
        title=f"Delete {_plural(len(contacts), 'contact')}",
        columns=["Name", "Email", "Company"],
        rows=[[c.name, c.email or "", c.company.name if c.company else ""] for c in contacts],
    )
    names = [c.name for c in contacts]
    for contact in contacts:
        await service.delete_with_objects(deps.session, deps.store, contact)
    return Deleted(deleted=names)


# --- Companies ---------------------------------------------------------------------


@_read_tool
async def search_companies(
    ctx: RunContext[AgentDeps], *, q: str | None = None, page: int = 1
) -> Page[CompanySearchRow]:
    """Find companies, each with how many contacts it has and when any of them was
    last contacted.

    Args:
        q: Matches name, website, or industry (case-insensitive).
        page: 1-based page of 20.
    """
    if page < 1:
        raise retry("page starts at 1.")
    deps = ctx.deps
    query = companies_query(deps.membership, CompanyFilters(q=q))
    total = await _count(deps.session, query)
    limit, offset = _page_bounds(page)
    stats = (
        select(
            Contact.company_id,
            func.count(Contact.id).label("contact_count"),
            func.max(Contact.last_contacted_at).label("latest"),
        )
        .where(Contact.workspace_id == deps.workspace_id)
        .group_by(Contact.company_id)
        .subquery()
    )
    rows = await deps.session.execute(
        query.add_columns(func.coalesce(stats.c.contact_count, 0), stats.c.latest)
        .outerjoin(stats, stats.c.company_id == Company.id)
        .limit(limit)
        .offset(offset)
    )
    items = [
        CompanySearchRow(
            **_company_row(deps, company).model_dump(),
            contact_count=count,
            latest_contact_at=latest,
        )
        for company, count, latest in rows
    ]
    return Page(items=items, total=total, page=page, next_page=_next_page(page, len(items), total))


@_read_tool
async def get_company(ctx: RunContext[AgentDeps], company_id: uuid.UUID) -> CompanyDetail:
    """One company with its notes, up to 20 of its contacts, and attached files."""
    deps = ctx.deps
    company = await _owned(deps, Company, company_id)
    contacts_q = select(Contact).where(Contact.company_id == company.id)
    total = await _count(deps.session, contacts_q)
    contacts = await deps.session.scalars(
        contacts_q.options(selectinload(Contact.company))
        .order_by(Contact.name, Contact.id)
        .limit(PAGE_SIZE)
    )
    rows = [_contact_row(deps, c) for c in contacts]
    return CompanyDetail(
        company=_company_row(deps, company),
        notes=company.notes,
        contacts=rows,
        more_contacts=max(0, total - len(rows)),
        attachments=await _attachments_of(deps, company),
        created_at=company.created_at,
    )


@_write_tool
async def create_companies(
    ctx: RunContext[AgentDeps], items: list[CompanyItem]
) -> CompaniesCreated:
    """Create companies. One item runs at once; more than one pauses for the user's
    approval. Files from the chat can be attached with `upload_ids`."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    for item in items:
        await _chat_uploads(deps, item.upload_ids)
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Create {_plural(len(items), 'company')}".replace("companys", "companies"),
            columns=["Name", "Website", "Industry"],
            rows=[[item.name, item.website or "", item.industry or ""] for item in items],
        )
    result = CompaniesCreated(created=[], attached=[])
    for item in items:
        body = CompanyCreate(**item.model_dump(include=set(CompanyCreate.model_fields)))
        company = await service.create_company(
            deps.session, deps.membership, body, source=RowSource.AGENT
        )
        for upload in await _chat_uploads(deps, item.upload_ids):
            result.attached.append(_attachment_row(deps, _attach(deps, upload, company)))
        result.created.append(_company_row(deps, company))
    await deps.session.commit()
    return result


@_write_tool
async def update_companies(
    ctx: RunContext[AgentDeps], items: list[CompanyChange]
) -> list[CompanyRow]:
    """Change companies: name, website, industry, or notes. One item runs at once;
    more than one pauses for approval."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    companies = await _owned_all(deps, Company, [item.company_id for item in items])
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Update {len(items)} companies",
            columns=["Company", "Changes"],
            rows=[
                [company.name, _short(item.changes.model_dump(exclude_unset=True), 80)]
                for company, item in zip(companies, items, strict=True)
            ],
        )
    updated = [
        await service.update_company(deps.session, deps.membership, item.company_id, item.changes)
        for item in items
    ]
    await deps.session.commit()
    return [_company_row(deps, c) for c in updated]


@_approval_tool
async def delete_companies(ctx: RunContext[AgentDeps], company_ids: list[uuid.UUID]) -> Deleted:
    """Delete companies and their attached files. Their contacts and tasks are kept,
    with the company link cleared. Always pauses for the user's approval."""
    _write_allowed(ctx)
    deps = ctx.deps
    companies = await _owned_all(deps, Company, company_ids)
    counted = await deps.session.execute(
        select(Contact.company_id, func.count(Contact.id))
        .where(Contact.company_id.in_([c.id for c in companies]))
        .group_by(Contact.company_id)
    )
    counts = dict(counted.tuples())
    await _pause_for_approval(
        ctx,
        title=f"Delete {len(companies)} companies" if len(companies) > 1 else "Delete 1 company",
        columns=["Name", "Contacts kept (link cleared)"],
        rows=[[c.name, str(counts.get(c.id, 0))] for c in companies],
    )
    names = [c.name for c in companies]
    for company in companies:
        await service.delete_with_objects(deps.session, deps.store, company)
    return Deleted(deleted=names)


# --- Activities --------------------------------------------------------------------


@_read_tool
async def list_activities(
    ctx: RunContext[AgentDeps], *, contact_id: uuid.UUID, page: int = 1
) -> Page[ActivityRow]:
    """A contact's activity feed, newest first: calls, emails, meetings, notes,
    follow-ups, and completed tasks.

    Args:
        contact_id: The contact.
        page: 1-based page of 20.
    """
    if page < 1:
        raise retry("page starts at 1.")
    deps = ctx.deps
    contact = await _owned(deps, Contact, contact_id)
    query = (
        select(Activity)
        .where(Activity.contact_id == contact.id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
    )
    total = await _count(deps.session, query)
    limit, offset = _page_bounds(page)
    items = [
        _activity_row(a) for a in await deps.session.scalars(query.limit(limit).offset(offset))
    ]
    return Page(items=items, total=total, page=page, next_page=_next_page(page, len(items), total))


@_write_tool
async def log_activities(
    ctx: RunContext[AgentDeps], items: list[ActivityItem]
) -> list[ActivityRow]:
    """Log a call, email, meeting, note, or follow-up on contacts. A call, email,
    meeting, or follow-up also marks the contact as contacted now. One item runs at
    once; more than one pauses for approval."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    if any(item.type is ActivityType.TASK_COMPLETED for item in items):
        raise retry("task_completed is logged by completing a task with update_tasks.")
    contacts = await _owned_all(deps, Contact, [item.contact_id for item in items])
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Log {_plural(len(items), 'activity')}".replace("activitys", "activities"),
            columns=["Contact", "Type", "Notes"],
            rows=[
                [contact.name, item.type.value, _short(item.notes)]
                for contact, item in zip(contacts, items, strict=True)
            ],
        )
    logged = [
        await service.create_activity(
            deps.session,
            deps.membership,
            item.contact_id,
            ActivityCreate(type=item.type, notes=item.notes),
            source=RowSource.AGENT,
        )
        for item in items
    ]
    await deps.session.commit()
    return [_activity_row(a) for a in logged]


# --- Tasks -------------------------------------------------------------------------


@_read_tool
async def list_tasks(  # noqa: PLR0913
    ctx: RunContext[AgentDeps],
    *,
    due: DueFilter | None = None,
    status: TaskStatus | None = TaskStatus.OPEN,
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    page: int = 1,
) -> Page[TaskRow]:
    """Tasks, soonest due first. "Today" follows the user's time zone.

    Args:
        due: `overdue` (before today), `today`, or `upcoming` (after today). Undated
            tasks match none of these.
        status: `open` (the default) or `done`; null for both.
        contact_id: Only tasks linked to this contact.
        company_id: Only tasks linked to this company.
        page: 1-based page of 20.
    """
    if page < 1:
        raise retry("page starts at 1.")
    deps = ctx.deps
    filters = TaskFilters(
        due=due, tz=deps.time_zone, status=status, contact_id=contact_id, company_id=company_id
    )
    query = tasks_query(deps.membership, filters)
    total = await _count(deps.session, query)
    limit, offset = _page_bounds(page)
    items = [
        _task_row(deps, t) for t in await deps.session.scalars(query.limit(limit).offset(offset))
    ]
    return Page(items=items, total=total, page=page, next_page=_next_page(page, len(items), total))


@_write_tool
async def create_tasks(ctx: RunContext[AgentDeps], items: list[TaskCreate]) -> list[TaskRow]:
    """Create tasks. `due_at` is an ISO 8601 datetime with a time zone offset: work out
    "next Tuesday" or "in two weeks" from today's date and the user's time zone, using
    09:00 when no time is given. One item runs at once; more than one pauses for
    approval."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Create {_plural(len(items), 'task')}",
            columns=["Title", "Due"],
            rows=[[item.title, item.due_at.isoformat() if item.due_at else ""] for item in items],
        )
    created = [
        await service.create_task(deps.session, deps.membership, item, source=RowSource.AGENT)
        for item in items
    ]
    await deps.session.commit()
    for task in created:
        await deps.session.refresh(task, ["contact", "company"])
    return [_task_row(deps, t) for t in created]


@_write_tool
async def update_tasks(ctx: RunContext[AgentDeps], items: list[TaskChange]) -> list[TaskRow]:
    """Change tasks, including completing (`status: done`) and reopening them. One
    item runs at once; more than one pauses for approval."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    tasks = await _owned_all(deps, Task, [item.task_id for item in items])
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Update {_plural(len(items), 'task')}",
            columns=["Task", "Changes"],
            rows=[
                [task.title, _short(item.changes.model_dump(exclude_unset=True), 80)]
                for task, item in zip(tasks, items, strict=True)
            ],
        )
    updated = [
        await service.update_task(
            deps.session, deps.membership, item.task_id, item.changes, source=RowSource.AGENT
        )
        for item in items
    ]
    await deps.session.commit()
    for task in updated:
        await deps.session.refresh(task, ["contact", "company"])
    return [_task_row(deps, t) for t in updated]


@_approval_tool
async def delete_tasks(ctx: RunContext[AgentDeps], task_ids: list[uuid.UUID]) -> Deleted:
    """Delete tasks. Always pauses for the user's approval."""
    _write_allowed(ctx)
    deps = ctx.deps
    tasks = await _owned_all(deps, Task, task_ids, selectinload(Task.contact))
    await _pause_for_approval(
        ctx,
        title=f"Delete {_plural(len(tasks), 'task')}",
        columns=["Title", "Contact", "Due"],
        rows=[
            [t.title, t.contact.name if t.contact else "", t.due_at.isoformat() if t.due_at else ""]
            for t in tasks
        ],
    )
    titles = [t.title for t in tasks]
    for task in tasks:
        await service.delete_task(deps.session, deps.membership, task.id)
    await deps.session.commit()
    return Deleted(deleted=titles)


# --- Attachments -------------------------------------------------------------------


async def _parent(
    deps: AgentDeps, contact_id: UUID | None, company_id: UUID | None
) -> Contact | Company:
    """The one record named by exactly one of the two ids."""
    if contact_id is not None and company_id is None:
        return await _owned(deps, Contact, contact_id)
    if company_id is not None and contact_id is None:
        return await _owned(deps, Company, company_id)
    raise retry("Pass exactly one of contact_id and company_id.")


@_read_tool
async def list_attachments(
    ctx: RunContext[AgentDeps],
    *,
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
) -> list[AttachmentRow]:
    """Files attached to a contact or a company, newest first, with download links.
    Pass exactly one of `contact_id` and `company_id`."""
    return await _attachments_of(ctx.deps, await _parent(ctx.deps, contact_id, company_id))


@_write_tool
async def attach_files(ctx: RunContext[AgentDeps], items: list[FileTarget]) -> list[AttachmentRow]:
    """Attach files the user dropped into this chat to existing contacts or companies.
    Each item names one upload and exactly one of `contact_id` or `company_id`. One
    item runs at once; more than one pauses for approval."""
    _write_allowed(ctx)
    _check_bulk(items)
    deps = ctx.deps
    uploads = await _chat_uploads(deps, [item.upload_id for item in items])
    parents = [await _parent(deps, item.contact_id, item.company_id) for item in items]
    if len(items) > 1:
        await _pause_for_approval(
            ctx,
            title=f"Attach {_plural(len(items), 'file')}",
            columns=["File", "To"],
            rows=[[u.filename, p.name] for u, p in zip(uploads, parents, strict=True)],
        )
    attached = [_attach(deps, u, p) for u, p in zip(uploads, parents, strict=True)]
    await deps.session.commit()
    return [_attachment_row(deps, a) for a in attached]


@_approval_tool
async def delete_attachments(
    ctx: RunContext[AgentDeps], attachment_ids: list[uuid.UUID]
) -> Deleted:
    """Delete attached files. Always pauses for the user's approval."""
    _write_allowed(ctx)
    deps = ctx.deps
    attachments = await _owned_all(deps, Attachment, attachment_ids)
    await _pause_for_approval(
        ctx,
        title=f"Delete {_plural(len(attachments), 'file')}",
        columns=["File", "Size"],
        rows=[[a.filename, f"{a.size} bytes"] for a in attachments],
    )
    names = [a.filename for a in attachments]
    for attachment in attachments:
        await service.delete_attachment(deps.session, deps.store, deps.membership, attachment.id)
    return Deleted(deleted=names)


# --- Workspace ---------------------------------------------------------------------


@_read_tool
async def get_workspace(ctx: RunContext[AgentDeps]) -> WorkspaceInfo:
    """The workspace this chat belongs to, the user's role in it, today's date, and
    their time zone."""
    deps = ctx.deps
    now = utcnow().astimezone(deps.time_zone)
    return WorkspaceInfo(
        id=deps.workspace_id,
        name=deps.membership.workspace.name,
        your_role=deps.membership.role.value,
        you_can_write=deps.membership.can(Permission.CRM_WRITE),
        today=now.date().isoformat(),
        time_zone=str(deps.time_zone),
    )


@_read_tool
async def list_members(ctx: RunContext[AgentDeps]) -> list[MemberRow]:
    """Who is in the workspace, by email and role. Use it to turn a name like "Bob"
    into a member when the user refers to a colleague."""
    deps = ctx.deps
    members = await deps.session.scalars(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == deps.workspace_id)
        .order_by(WorkspaceMember.created_at)
    )
    return [MemberRow(user_id=m.user_id, email=m.user.email, role=m.role.value) for m in members]


WRITE_TOOL_NAMES = frozenset(
    name for name, tool in toolset.tools.items() if _tool_tier(tool.metadata) != "read"
)
