from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.crm.attachments import delete_with_objects
from alloy_api.crm.common import (
    Page,
    PageOf,
    SortOrder,
    check_owned,
    fetch_owned,
    paginate,
    sorted_by,
)
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
from alloy_api.storage import ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/contacts", tags=["contacts"])

WITH_COMPANY = selectinload(Contact.company)


class ContactSort(StrEnum):
    NAME = "name"
    COMPANY = "company"
    STATUS = "status"
    LAST_CONTACTED_AT = "last_contacted_at"


SORT_COLUMNS = {
    ContactSort.NAME: Contact.name,
    ContactSort.COMPANY: Company.name,
    ContactSort.STATUS: Contact.status,
    ContactSort.LAST_CONTACTED_AT: Contact.last_contacted_at,
}


class ContactFilters(Page):
    q: str | None = Field(None, description="Matches name, email, phone, job title, or company.")
    status: ContactStatus | None = None
    company_id: UUID | None = None
    sort: ContactSort = ContactSort.NAME
    order: SortOrder = SortOrder.ASC


@router.get("/")
async def list_contacts(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[ContactFilters, Query()]
) -> PageOf[ContactRead]:
    """Sorted by name unless `sort` says otherwise; contacts without a value for the
    sort column come last either way."""
    query = (
        select(Contact).options(WITH_COMPANY).where(Contact.workspace_id == membership.workspace.id)
    )
    if filters.q or filters.sort is ContactSort.COMPANY:
        query = query.outerjoin(Contact.company)
    if filters.q:
        pattern = f"%{filters.q}%"
        query = query.where(
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
    query = sorted_by(query, SORT_COLUMNS[filters.sort], filters.order, Contact.id)
    return await paginate(session, query, filters, ContactRead)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate, session: SessionDep, membership: CanWriteCrm
) -> ContactRead:
    await check_owned(session, Company, body.company_id, membership)
    contact = Contact(
        workspace_id=membership.workspace.id, created_by=membership.user, **body.model_dump()
    )
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
    contact_id: UUID, session: SessionDep, store: ObjectStoreDep, membership: CanWriteCrm
) -> Response:
    """The contact's activities and attachments go with it; tasks are kept, with the
    link cleared."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    await delete_with_objects(session, store, contact)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{contact_id}/activities")
async def list_activities(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[ActivityRead]:
    """Newest first."""
    await fetch_owned(session, Contact, contact_id, membership)
    query = (
        select(Activity)
        .where(Activity.contact_id == contact_id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
    )
    return await paginate(session, query, page, ActivityRead)


@router.post("/{contact_id}/activities", status_code=status.HTTP_201_CREATED)
async def create_activity(
    contact_id: UUID, body: ActivityCreate, session: SessionDep, membership: CanWriteCrm
) -> ActivityRead:
    """A call, email, meeting, or follow-up also marks the contact as contacted now."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    now = utcnow()
    activity = Activity(
        contact_id=contact.id,
        type=body.type,
        notes=body.notes,
        created_by=membership.user,
        created_at=now,
    )
    session.add(activity)
    if body.type in CONTACT_ACTIVITY_TYPES:
        contact.last_contacted_at = now
    await session.commit()
    return ActivityRead.model_validate(activity)
