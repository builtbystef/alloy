from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.crm.common import Page, check_owned, fetch_owned
from alloy_api.crm.models import (
    CONTACT_ACTIVITY_TYPES,
    Activity,
    Company,
    Contact,
    ContactStatus,
)
from alloy_api.crm.schemas import (
    ActivityCreate,
    ActivityRead,
    ContactCreate,
    ContactRead,
    ContactUpdate,
)
from alloy_api.db import SessionDep
from alloy_api.models import utcnow
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/contacts", tags=["contacts"])

WITH_COMPANY = selectinload(Contact.company)


class ContactFilters(Page):
    q: str | None = Field(None, description="Matches name, email, phone, job title, or company.")
    status: ContactStatus | None = None
    company_id: UUID | None = None


@router.get("/")
async def list_contacts(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[ContactFilters, Query()]
) -> list[ContactRead]:
    """Sorted by name."""
    query = (
        select(Contact).options(WITH_COMPANY).where(Contact.workspace_id == membership.workspace.id)
    )
    if filters.q:
        pattern = f"%{filters.q}%"
        query = query.outerjoin(Contact.company).where(
            Contact.name.ilike(pattern)
            | Contact.email.ilike(pattern)
            | Contact.phone.ilike(pattern)
            | Contact.job_title.ilike(pattern)
            | Company.name.ilike(pattern)
        )
    if filters.status is not None:
        query = query.where(Contact.status == filters.status)
    if filters.company_id is not None:
        query = query.where(Contact.company_id == filters.company_id)
    query = query.order_by(Contact.name, Contact.id).limit(filters.limit).offset(filters.offset)
    return [ContactRead.model_validate(c) for c in await session.scalars(query)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate, session: SessionDep, membership: CanWriteCrm
) -> ContactRead:
    await check_owned(session, Company, body.company_id, membership)
    contact = Contact(workspace_id=membership.workspace.id, **body.model_dump())
    session.add(contact)
    await session.commit()
    await session.refresh(contact, ["company"])
    return ContactRead.model_validate(contact)


@router.get("/{contact_id}")
async def read_contact(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm
) -> ContactRead:
    contact = await fetch_owned(session, Contact, contact_id, membership, WITH_COMPANY)
    return ContactRead.model_validate(contact)


@router.patch("/{contact_id}")
async def update_contact(
    contact_id: UUID, body: ContactUpdate, session: SessionDep, membership: CanWriteCrm
) -> ContactRead:
    contact = await fetch_owned(session, Contact, contact_id, membership)
    changes = body.model_dump(exclude_unset=True)
    if "company_id" in changes:
        await check_owned(session, Company, changes["company_id"], membership)
    for field, value in changes.items():
        setattr(contact, field, value)
    await session.commit()
    await session.refresh(contact, ["company"])
    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID, session: SessionDep, membership: CanWriteCrm
) -> Response:
    """The contact's activities go with it; tasks are kept, with the link cleared."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    await session.delete(contact)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Activity feed


@router.get("/{contact_id}/activities")
async def list_activities(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> list[ActivityRead]:
    """Newest first."""
    await fetch_owned(session, Contact, contact_id, membership)
    query = (
        select(Activity)
        .where(Activity.contact_id == contact_id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    return [ActivityRead.model_validate(a) for a in await session.scalars(query)]


@router.post("/{contact_id}/activities", status_code=status.HTTP_201_CREATED)
async def create_activity(
    contact_id: UUID, body: ActivityCreate, session: SessionDep, membership: CanWriteCrm
) -> ActivityRead:
    """A call, email, meeting, or follow-up also marks the contact as contacted now."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    now = utcnow()
    activity = Activity(contact_id=contact.id, type=body.type, notes=body.notes, created_at=now)
    session.add(activity)
    if body.type in CONTACT_ACTIVITY_TYPES:
        contact.last_contacted_at = now
    await session.commit()
    return ActivityRead.model_validate(activity)
