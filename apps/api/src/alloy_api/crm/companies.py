from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.crm.attachments import delete_with_objects
from alloy_api.crm.common import Page, PageOf, SortOrder, fetch_owned, paginate, sorted_by
from alloy_api.crm.models import Company, Contact
from alloy_api.crm.schemas import CompanyCreate, CompanyRead, CompanyUpdate, ContactRead
from alloy_api.db import SessionDep
from alloy_api.storage import ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanySort(StrEnum):
    NAME = "name"
    INDUSTRY = "industry"
    CREATED_AT = "created_at"


SORT_COLUMNS = {
    CompanySort.NAME: Company.name,
    CompanySort.INDUSTRY: Company.industry,
    CompanySort.CREATED_AT: Company.created_at,
}


class CompanyFilters(Page):
    q: str | None = Field(None, description="Matches name, website, or industry.")
    sort: CompanySort = CompanySort.NAME
    order: SortOrder = SortOrder.ASC


@router.get("/")
async def list_companies(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[CompanyFilters, Query()]
) -> PageOf[CompanyRead]:
    """Sorted by name unless `sort` says otherwise; companies without a value for the
    sort column come last either way."""
    query = select(Company).where(Company.workspace_id == membership.workspace.id)
    if filters.q:
        pattern = f"%{filters.q}%"
        query = query.where(
            Company.name.ilike(pattern)
            | Company.website.ilike(pattern)
            | Company.industry.ilike(pattern)
        )
    query = sorted_by(query, SORT_COLUMNS[filters.sort], filters.order, Company.id)
    return await paginate(session, query, filters, CompanyRead)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate, session: SessionDep, membership: CanWriteCrm
) -> CompanyRead:
    company = Company(
        workspace_id=membership.workspace.id, created_by=membership.user, **body.model_dump()
    )
    session.add(company)
    await session.commit()
    return CompanyRead.model_validate(company)


@router.get("/{company_id}")
async def read_company(
    company_id: UUID, session: SessionDep, membership: CanReadCrm
) -> CompanyRead:
    return CompanyRead.model_validate(await fetch_owned(session, Company, company_id, membership))


@router.patch("/{company_id}")
async def update_company(
    company_id: UUID, body: CompanyUpdate, session: SessionDep, membership: CanWriteCrm
) -> CompanyRead:
    company = await fetch_owned(session, Company, company_id, membership)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await session.commit()
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID, session: SessionDep, store: ObjectStoreDep, membership: CanWriteCrm
) -> Response:
    """Contacts and tasks at the company are kept, with the link cleared; its
    attachments go with it."""
    company = await fetch_owned(session, Company, company_id, membership)
    await delete_with_objects(session, store, company)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{company_id}/contacts")
async def list_company_contacts(
    company_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[ContactRead]:
    """Sorted by name. `GET .../contacts/?company_id=` is the same list with filters
    and sorting."""
    await fetch_owned(session, Company, company_id, membership)
    query = (
        select(Contact)
        .options(selectinload(Contact.company))
        .where(Contact.company_id == company_id)
        .order_by(Contact.name, Contact.id)
    )
    return await paginate(session, query, page, ContactRead)
