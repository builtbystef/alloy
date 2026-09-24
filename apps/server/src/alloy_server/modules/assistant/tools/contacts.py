import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from pydantic_ai import RunContext
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_server.db.base import utcnow
from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.tools.common import (
    activity_row,
    attach,
    attachment_row,
    attachments_of,
    chat_uploads,
    check_bulk,
    company_row,
    contact_row,
    count_rows,
    next_page,
    owned,
    owned_all,
    page_bounds,
    pause_for_approval,
    plural,
    short,
    task_row,
    write_allowed,
)
from alloy_server.modules.assistant.tools.registry import (
    approval_tool,
    read_tool,
    retry,
    write_tool,
)
from alloy_server.modules.assistant.tools.shapes import (
    CompanyGroup,
    ContactChange,
    ContactDetail,
    ContactItem,
    ContactRow,
    ContactsCreated,
    Deleted,
    GroupedContacts,
    Page,
    Skipped,
)
from alloy_server.modules.crm.companies.models import Company
from alloy_server.modules.crm.contacts import service as contact_service
from alloy_server.modules.crm.contacts.models import Activity, Contact, ContactStatus
from alloy_server.modules.crm.contacts.schemas import ContactCreate, ContactFilters
from alloy_server.modules.crm.models import RowSource
from alloy_server.modules.crm.tasks import service as task_service
from alloy_server.modules.crm.tasks.models import Task, TaskStatus

if TYPE_CHECKING:
    from uuid import UUID


async def _resolve_company(deps: AgentDeps, item: ContactItem) -> UUID | None:
    if item.company_id is not None:
        await owned(deps, Company, item.company_id)
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


@read_tool
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
    query = contact_service.contacts_query(deps.membership, filters)
    if stale_days is not None:
        if stale_days < 1:
            raise retry("stale_days must be at least 1.")
        stale_before = utcnow() - timedelta(days=stale_days)
        query = (
            query.order_by(None)
            .where(Contact.last_contacted_at.is_(None) | (Contact.last_contacted_at < stale_before))
            .order_by(Contact.last_contacted_at.asc().nulls_first(), Contact.name, Contact.id)
        )
    total = await count_rows(deps.session, query)
    limit, offset = page_bounds(page)
    contacts = list(await deps.session.scalars(query.limit(limit).offset(offset)))
    rows = [contact_row(deps, c) for c in contacts]
    if not group_by_company:
        return Page(items=rows, total=total, page=page, next_page=next_page(page, len(rows), total))
    groups: dict[UUID | None, CompanyGroup] = {}
    for contact, row in zip(contacts, rows, strict=True):
        group = groups.get(contact.company_id)
        if group is None:
            company = company_row(deps, contact.company) if contact.company else None
            group = groups[contact.company_id] = CompanyGroup(company=company, contacts=[])
        group.contacts.append(row)
    return GroupedContacts(
        groups=list(groups.values()),
        total=total,
        page=page,
        next_page=next_page(page, len(rows), total),
    )


@read_tool
async def get_contact(ctx: RunContext[AgentDeps], contact_id: uuid.UUID) -> ContactDetail:
    """Everything about one contact: details, the five most recent activities, open
    tasks, and attached files."""
    deps = ctx.deps
    contact = await owned(deps, Contact, contact_id, selectinload(Contact.company))
    activities = await deps.session.scalars(
        select(Activity)
        .where(Activity.contact_id == contact.id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(5)
    )
    tasks = await deps.session.scalars(
        select(Task)
        .options(*task_service.WITH_RELATIONS)
        .where(Task.contact_id == contact.id, Task.status == TaskStatus.OPEN)
        .order_by(Task.due_at.asc().nulls_last(), Task.id)
    )
    return ContactDetail(
        contact=contact_row(deps, contact),
        phone=contact.phone,
        recent_activities=[activity_row(a) for a in activities],
        open_tasks=[task_row(deps, t) for t in tasks],
        attachments=await attachments_of(deps, contact),
        created_at=contact.created_at,
    )


@write_tool
async def create_contacts(ctx: RunContext[AgentDeps], items: list[ContactItem]) -> ContactsCreated:
    """Create contacts. One item runs at once; more than one pauses for the user's
    approval. An item whose email already belongs to a contact is skipped and the
    existing contact returned, unless `allow_duplicate_email` is set. Files from the
    chat can be attached with `upload_ids`."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    company_ids = [await _resolve_company(deps, item) for item in items]
    for item in items:
        await chat_uploads(deps, item.upload_ids)
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Create {plural(len(items), 'contact')}",
            columns=["Name", "Email", "Company"],
            rows=[[item.name, item.email or "", item.company_name or ""] for item in items],
        )
    result = ContactsCreated(created=[], skipped=[], attached=[])
    # An email created earlier in this call is as much a duplicate as one in the table.
    created_by_email: dict[str, ContactRow] = {}
    for item, company_id in zip(items, company_ids, strict=True):
        email = item.email.lower() if item.email else None
        existing: ContactRow | None = None
        if email is not None and not item.allow_duplicate_email:
            existing = created_by_email.get(email)
            if existing is None and (row := await _duplicate_by_email(deps, email)) is not None:
                existing = contact_row(deps, row)
        if existing is not None:
            result.skipped.append(
                Skipped(
                    name=item.name,
                    reason=f"A contact with the email {item.email} already exists.",
                    existing=existing,
                )
            )
            continue
        body = ContactCreate(**item.model_dump(include=set(ContactCreate.model_fields)))
        body.company_id = company_id
        contact = await contact_service.create_contact(
            deps.session, deps.membership, body, source=RowSource.AGENT
        )
        for upload in await chat_uploads(deps, item.upload_ids):
            result.attached.append(attachment_row(deps, attach(deps, upload, contact)))
        await deps.session.flush()
        await deps.session.refresh(contact, ["company"])
        created = contact_row(deps, contact)
        result.created.append(created)
        if email is not None:
            created_by_email[email] = created
    await deps.session.commit()
    return result


@write_tool
async def update_contacts(
    ctx: RunContext[AgentDeps], items: list[ContactChange]
) -> list[ContactRow]:
    """Change contacts: name, email, phone, job title, company, status, or last
    contacted date. One item runs at once; more than one pauses for approval."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    contacts = await owned_all(deps, Contact, [item.contact_id for item in items])
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Update {plural(len(items), 'contact')}",
            columns=["Contact", "Changes"],
            rows=[
                [contact.name, short(item.changes.model_dump(exclude_unset=True), 80)]
                for contact, item in zip(contacts, items, strict=True)
            ],
        )
    updated = [
        await contact_service.update_contact(
            deps.session, deps.membership, item.contact_id, item.changes
        )
        for item in items
    ]
    await deps.session.commit()
    for contact in updated:
        await deps.session.refresh(contact, ["company"])
    return [contact_row(deps, c) for c in updated]


@approval_tool
async def delete_contacts(ctx: RunContext[AgentDeps], contact_ids: list[uuid.UUID]) -> Deleted:
    """Delete contacts, with their activities and attached files. Tasks linked to them
    are kept. Always pauses for the user's approval."""
    write_allowed(ctx)
    deps = ctx.deps
    contacts = await owned_all(deps, Contact, contact_ids, selectinload(Contact.company))
    await pause_for_approval(
        ctx,
        title=f"Delete {plural(len(contacts), 'contact')}",
        columns=["Name", "Email", "Company"],
        rows=[[c.name, c.email or "", c.company.name if c.company else ""] for c in contacts],
    )
    names = [c.name for c in contacts]
    for contact in contacts:
        await contact_service.delete_contact(deps.session, deps.store, contact)
    return Deleted(deleted=names)
