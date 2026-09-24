"""Company tools."""

import uuid

from pydantic_ai import RunContext
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.tools.common import (
    PAGE_SIZE,
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
    write_allowed,
)
from alloy_server.modules.assistant.tools.registry import (
    approval_tool,
    read_tool,
    retry,
    write_tool,
)
from alloy_server.modules.assistant.tools.shapes import (
    CompaniesCreated,
    CompanyChange,
    CompanyDetail,
    CompanyItem,
    CompanyRow,
    CompanySearchRow,
    Deleted,
    Page,
)
from alloy_server.modules.crm.companies import service as company_service
from alloy_server.modules.crm.companies.models import Company
from alloy_server.modules.crm.companies.schemas import CompanyCreate, CompanyFilters
from alloy_server.modules.crm.contacts.models import Contact
from alloy_server.modules.crm.models import RowSource


@read_tool
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
    query = company_service.companies_query(deps.membership, CompanyFilters(q=q))
    total = await count_rows(deps.session, query)
    limit, offset = page_bounds(page)
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
            **company_row(deps, company).model_dump(),
            contact_count=count,
            latest_contact_at=latest,
        )
        for company, count, latest in rows
    ]
    return Page(items=items, total=total, page=page, next_page=next_page(page, len(items), total))


@read_tool
async def get_company(ctx: RunContext[AgentDeps], company_id: uuid.UUID) -> CompanyDetail:
    """One company with its notes, up to 20 of its contacts, and attached files."""
    deps = ctx.deps
    company = await owned(deps, Company, company_id)
    contacts_q = select(Contact).where(Contact.company_id == company.id)
    total = await count_rows(deps.session, contacts_q)
    contacts = await deps.session.scalars(
        contacts_q.options(selectinload(Contact.company))
        .order_by(Contact.name, Contact.id)
        .limit(PAGE_SIZE)
    )
    rows = [contact_row(deps, c) for c in contacts]
    return CompanyDetail(
        company=company_row(deps, company),
        notes=company.notes,
        contacts=rows,
        more_contacts=max(0, total - len(rows)),
        attachments=await attachments_of(deps, company),
        created_at=company.created_at,
    )


@write_tool
async def create_companies(
    ctx: RunContext[AgentDeps], items: list[CompanyItem]
) -> CompaniesCreated:
    """Create companies. One item runs at once; more than one pauses for the user's
    approval. Files from the chat can be attached with `upload_ids`."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    for item in items:
        await chat_uploads(deps, item.upload_ids)
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Create {plural(len(items), 'company')}".replace("companys", "companies"),
            columns=["Name", "Website", "Industry"],
            rows=[[item.name, item.website or "", item.industry or ""] for item in items],
        )
    result = CompaniesCreated(created=[], attached=[])
    for item in items:
        body = CompanyCreate(**item.model_dump(include=set(CompanyCreate.model_fields)))
        company = await company_service.create_company(
            deps.session, deps.membership, body, source=RowSource.AGENT
        )
        for upload in await chat_uploads(deps, item.upload_ids):
            result.attached.append(attachment_row(deps, attach(deps, upload, company)))
        result.created.append(company_row(deps, company))
    await deps.session.commit()
    return result


@write_tool
async def update_companies(
    ctx: RunContext[AgentDeps], items: list[CompanyChange]
) -> list[CompanyRow]:
    """Change companies: name, website, industry, or notes. One item runs at once;
    more than one pauses for approval."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    companies = await owned_all(deps, Company, [item.company_id for item in items])
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Update {len(items)} companies",
            columns=["Company", "Changes"],
            rows=[
                [company.name, short(item.changes.model_dump(exclude_unset=True), 80)]
                for company, item in zip(companies, items, strict=True)
            ],
        )
    updated = [
        await company_service.update_company(
            deps.session, deps.membership, item.company_id, item.changes
        )
        for item in items
    ]
    await deps.session.commit()
    return [company_row(deps, c) for c in updated]


@approval_tool
async def delete_companies(ctx: RunContext[AgentDeps], company_ids: list[uuid.UUID]) -> Deleted:
    """Delete companies and their attached files. Their contacts and tasks are kept,
    with the company link cleared. Always pauses for the user's approval."""
    write_allowed(ctx)
    deps = ctx.deps
    companies = await owned_all(deps, Company, company_ids)
    counted = await deps.session.execute(
        select(Contact.company_id, func.count(Contact.id))
        .where(Contact.company_id.in_([c.id for c in companies]))
        .group_by(Contact.company_id)
    )
    counts = dict(counted.tuples())
    await pause_for_approval(
        ctx,
        title=f"Delete {len(companies)} companies" if len(companies) > 1 else "Delete 1 company",
        columns=["Name", "Contacts kept (link cleared)"],
        rows=[[c.name, str(counts.get(c.id, 0))] for c in companies],
    )
    names = [c.name for c in companies]
    for company in companies:
        await company_service.delete_company(deps.session, deps.store, company)
    return Deleted(deleted=names)
