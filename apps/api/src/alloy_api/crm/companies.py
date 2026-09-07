from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.auth.deps import CurrentUserDep
from alloy_api.crm.common import Page, fetch_owned
from alloy_api.crm.models import Company, Contact
from alloy_api.crm.schemas import CompanyCreate, CompanyRead, CompanyUpdate, ContactRead
from alloy_api.db import SessionDep

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyFilters(Page):
    q: str | None = Field(None, description="Matches name, website, or industry.")


@router.get("/")
async def list_companies(
    session: SessionDep, user: CurrentUserDep, filters: Annotated[CompanyFilters, Query()]
) -> list[CompanyRead]:
    """Sorted by name."""
    query = select(Company).where(Company.user_id == user.id)
    if filters.q:
        pattern = f"%{filters.q}%"
        query = query.where(
            Company.name.ilike(pattern)
            | Company.website.ilike(pattern)
            | Company.industry.ilike(pattern)
        )
    query = query.order_by(Company.name, Company.id).limit(filters.limit).offset(filters.offset)
    return [CompanyRead.model_validate(c) for c in await session.scalars(query)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate, session: SessionDep, user: CurrentUserDep
) -> CompanyRead:
    company = Company(user_id=user.id, **body.model_dump())
    session.add(company)
    await session.commit()
    return CompanyRead.model_validate(company)


@router.get("/{company_id}")
async def read_company(company_id: UUID, session: SessionDep, user: CurrentUserDep) -> CompanyRead:
    return CompanyRead.model_validate(await fetch_owned(session, Company, company_id, user))


@router.patch("/{company_id}")
async def update_company(
    company_id: UUID, body: CompanyUpdate, session: SessionDep, user: CurrentUserDep
) -> CompanyRead:
    company = await fetch_owned(session, Company, company_id, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await session.commit()
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: UUID, session: SessionDep, user: CurrentUserDep) -> Response:
    """Contacts and tasks at the company are kept, with the link cleared."""
    company = await fetch_owned(session, Company, company_id, user)
    await session.delete(company)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{company_id}/contacts")
async def list_company_contacts(
    company_id: UUID, session: SessionDep, user: CurrentUserDep
) -> list[ContactRead]:
    await fetch_owned(session, Company, company_id, user)
    query = (
        select(Contact)
        .options(selectinload(Contact.company))
        .where(Contact.company_id == company_id)
        .order_by(Contact.name, Contact.id)
    )
    return [ContactRead.model_validate(c) for c in await session.scalars(query)]
