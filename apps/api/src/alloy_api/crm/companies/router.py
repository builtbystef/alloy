from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from alloy_api.crm.companies import service
from alloy_api.crm.companies.schemas import (
    CompanyCreate,
    CompanyFilters,
    CompanyRead,
    CompanyUpdate,
)
from alloy_api.crm.contacts import service as contacts
from alloy_api.crm.contacts.schemas import ContactRead
from alloy_api.crm.pagination import Page, PageOf, paginate
from alloy_api.db.session import SessionDep
from alloy_api.integrations.storage import ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/")
async def list_companies(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[CompanyFilters, Query()]
) -> PageOf[CompanyRead]:
    """Sorted by name unless `sort` says otherwise; companies without a value for the
    sort column come last either way."""
    return await paginate(
        session, service.companies_query(membership, filters), filters, CompanyRead
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate, session: SessionDep, membership: CanWriteCrm
) -> CompanyRead:
    company = await service.create_company(session, membership, body)
    await session.commit()
    return CompanyRead.model_validate(company)


@router.get("/{company_id}")
async def read_company(
    company_id: UUID, session: SessionDep, membership: CanReadCrm
) -> CompanyRead:
    return CompanyRead.model_validate(await service.get_company(session, membership, company_id))


@router.patch("/{company_id}")
async def update_company(
    company_id: UUID, body: CompanyUpdate, session: SessionDep, membership: CanWriteCrm
) -> CompanyRead:
    company = await service.update_company(session, membership, company_id, body)
    await session.commit()
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID, session: SessionDep, store: ObjectStoreDep, membership: CanWriteCrm
) -> Response:
    """Contacts and tasks at the company are kept, with the link cleared; its
    attachments go with it."""
    company = await service.get_company(session, membership, company_id)
    await service.delete_company(session, store, company)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{company_id}/contacts")
async def list_company_contacts(
    company_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[ContactRead]:
    """Sorted by name. `GET .../contacts/?company_id=` is the same list with filters
    and sorting."""
    company = await service.get_company(session, membership, company_id)
    return await paginate(session, contacts.company_contacts_query(company), page, ContactRead)
