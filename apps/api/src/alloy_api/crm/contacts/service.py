from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.crm.attachments.service import delete_with_attachments
from alloy_api.crm.companies.models import Company
from alloy_api.crm.contacts.models import CONTACT_ACTIVITY_TYPES, Activity, Contact
from alloy_api.crm.contacts.schemas import ContactSort
from alloy_api.crm.ownership import check_owned, fetch_owned
from alloy_api.crm.pagination import sorted_by
from alloy_api.db.base import utcnow

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.crm.contacts.schemas import (
        ActivityCreate,
        ContactCreate,
        ContactFilters,
        ContactUpdate,
    )
    from alloy_api.crm.models import RowSource
    from alloy_api.integrations.storage import ObjectStore
    from alloy_api.workspaces.deps import Membership

WITH_COMPANY = selectinload(Contact.company)

SORT_COLUMNS = {
    ContactSort.NAME: Contact.name,
    ContactSort.COMPANY: Company.name,
    ContactSort.STATUS: Contact.status,
    ContactSort.LAST_CONTACTED_AT: Contact.last_contacted_at,
}


def contacts_query(membership: Membership, filters: ContactFilters) -> Select[tuple[Contact]]:
    """The workspace's contacts, filtered and sorted. Shared with the assistant."""
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
    return sorted_by(query, SORT_COLUMNS[filters.sort], filters.order, Contact.id)


def company_contacts_query(company: Company) -> Select[tuple[Contact]]:
    return (
        select(Contact)
        .options(WITH_COMPANY)
        .where(Contact.company_id == company.id)
        .order_by(Contact.name, Contact.id)
    )


def activities_query(contact: Contact) -> Select[tuple[Activity]]:
    return (
        select(Activity)
        .where(Activity.contact_id == contact.id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
    )


async def get_contact(session: AsyncSession, membership: Membership, contact_id: UUID) -> Contact:
    return await fetch_owned(session, Contact, contact_id, membership, WITH_COMPANY)


async def create_contact(
    session: AsyncSession,
    membership: Membership,
    body: ContactCreate,
    *,
    source: RowSource | None = None,
) -> Contact:
    await check_owned(session, Company, body.company_id, membership)
    contact = Contact(
        workspace_id=membership.workspace.id,
        created_by=membership.user,
        source=source,
        **body.model_dump(),
    )
    session.add(contact)
    await session.flush()
    return contact


async def update_contact(
    session: AsyncSession, membership: Membership, contact_id: UUID, body: ContactUpdate
) -> Contact:
    """Fields left out of `body` are untouched; fields sent as null are cleared."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    changes = body.model_dump(exclude_unset=True)
    if "company_id" in changes:
        await check_owned(session, Company, changes["company_id"], membership)
    for field, value in changes.items():
        setattr(contact, field, value)
    await session.flush()
    return contact


async def delete_contact(session: AsyncSession, store: ObjectStore, contact: Contact) -> None:
    """The contact's activities and attachments go with it; tasks are kept, with the
    link cleared. Commits."""
    await delete_with_attachments(session, store, contact)


async def create_activity(
    session: AsyncSession,
    membership: Membership,
    contact_id: UUID,
    body: ActivityCreate,
    *,
    source: RowSource | None = None,
) -> Activity:
    """A call, email, meeting, or follow-up also marks the contact as contacted now."""
    contact = await fetch_owned(session, Contact, contact_id, membership)
    now = utcnow()
    activity = Activity(
        contact_id=contact.id,
        type=body.type,
        notes=body.notes,
        created_by=membership.user,
        source=source,
        created_at=now,
    )
    session.add(activity)
    if body.type in CONTACT_ACTIVITY_TYPES:
        contact.last_contacted_at = now
    await session.flush()
    return activity
