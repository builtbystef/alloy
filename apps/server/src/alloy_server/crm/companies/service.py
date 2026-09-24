from typing import TYPE_CHECKING

from sqlalchemy import select

from alloy_server.crm.attachments.service import delete_with_attachments
from alloy_server.crm.companies.models import Company
from alloy_server.crm.companies.schemas import CompanySort
from alloy_server.crm.ownership import fetch_owned
from alloy_server.crm.pagination import sorted_by

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.crm.companies.schemas import CompanyCreate, CompanyFilters, CompanyUpdate
    from alloy_server.crm.models import RowSource
    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.workspaces.dependencies import Membership

SORT_COLUMNS = {
    CompanySort.NAME: Company.name,
    CompanySort.INDUSTRY: Company.industry,
    CompanySort.CREATED_AT: Company.created_at,
}


def companies_query(membership: Membership, filters: CompanyFilters) -> Select[tuple[Company]]:
    """The workspace's companies, filtered and sorted. Shared with the assistant."""
    query = select(Company).where(Company.workspace_id == membership.workspace.id)
    if filters.q:
        query = query.where(
            Company.name.icontains(filters.q, autoescape=True)
            | Company.website.icontains(filters.q, autoescape=True)
            | Company.industry.icontains(filters.q, autoescape=True)
        )
    return sorted_by(query, SORT_COLUMNS[filters.sort], filters.order, Company.id)


async def get_company(session: AsyncSession, membership: Membership, company_id: UUID) -> Company:
    return await fetch_owned(session, Company, company_id, membership)


async def create_company(
    session: AsyncSession,
    membership: Membership,
    body: CompanyCreate,
    *,
    source: RowSource | None = None,
) -> Company:
    company = Company(
        workspace_id=membership.workspace.id,
        created_by=membership.user,
        source=source,
        **body.model_dump(),
    )
    session.add(company)
    await session.flush()
    return company


async def update_company(
    session: AsyncSession, membership: Membership, company_id: UUID, body: CompanyUpdate
) -> Company:
    """Fields left out of `body` are untouched; fields sent as null are cleared."""
    company = await fetch_owned(session, Company, company_id, membership)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await session.flush()
    return company


async def delete_company(session: AsyncSession, store: ObjectStore, company: Company) -> None:
    """Contacts and tasks at the company are kept, with the link cleared; its
    attachments go with it. Commits."""
    await delete_with_attachments(session, store, company)
