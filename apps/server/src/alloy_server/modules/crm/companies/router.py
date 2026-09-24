from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from alloy_server.db.session import SessionDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.modules.crm.companies import service
from alloy_server.modules.crm.companies.schemas import (
    CompanyCreate,
    CompanyFilters,
    CompanyResponse,
    CompanyUpdate,
)
from alloy_server.modules.crm.contacts import service as contacts
from alloy_server.modules.crm.contacts.schemas import ContactResponse
from alloy_server.modules.crm.pagination import Page, PageOf, paginate
from alloy_server.modules.workspaces.dependencies import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/")
async def list_companies(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[CompanyFilters, Query()]
) -> PageOf[CompanyResponse]:
    """Sorted by name unless `sort` says otherwise; companies without a value for the
    sort column come last either way."""
    return await paginate(
        session, service.companies_query(membership, filters), filters, CompanyResponse
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate, session: SessionDep, membership: CanWriteCrm
) -> CompanyResponse:
    company = await service.create_company(session, membership, body)
    await session.commit()
    return CompanyResponse.model_validate(company)


@router.get("/{company_id}")
async def read_company(
    company_id: UUID, session: SessionDep, membership: CanReadCrm
) -> CompanyResponse:
    return CompanyResponse.model_validate(
        await service.get_company(session, membership, company_id)
    )


@router.patch("/{company_id}")
async def update_company(
    company_id: UUID, body: CompanyUpdate, session: SessionDep, membership: CanWriteCrm
) -> CompanyResponse:
    company = await service.update_company(session, membership, company_id, body)
    await session.commit()
    return CompanyResponse.model_validate(company)


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
) -> PageOf[ContactResponse]:
    """Sorted by name. `GET .../contacts/?company_id=` is the same list with filters
    and sorting."""
    company = await service.get_company(session, membership, company_id)
    return await paginate(session, contacts.company_contacts_query(company), page, ContactResponse)
