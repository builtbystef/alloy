from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from alloy_api.crm.contacts import service
from alloy_api.crm.contacts.schemas import (
    ActivityCreate,
    ActivityRead,
    ContactCreate,
    ContactFilters,
    ContactRead,
    ContactUpdate,
)
from alloy_api.crm.pagination import Page, PageOf, paginate
from alloy_api.db.session import SessionDep
from alloy_api.integrations.storage import ObjectStoreDep
from alloy_api.workspaces.deps import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/")
async def list_contacts(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[ContactFilters, Query()]
) -> PageOf[ContactRead]:
    """Sorted by name unless `sort` says otherwise; contacts without a value for the
    sort column come last either way."""
    return await paginate(
        session, service.contacts_query(membership, filters), filters, ContactRead
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate, session: SessionDep, membership: CanWriteCrm
) -> ContactRead:
    contact = await service.create_contact(session, membership, body)
    await session.commit()
    await session.refresh(contact, ["company"])
    return ContactRead.model_validate(contact)


@router.get("/{contact_id}")
async def read_contact(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm
) -> ContactRead:
    return ContactRead.model_validate(await service.get_contact(session, membership, contact_id))


@router.patch("/{contact_id}")
async def update_contact(
    contact_id: UUID, body: ContactUpdate, session: SessionDep, membership: CanWriteCrm
) -> ContactRead:
    contact = await service.update_contact(session, membership, contact_id, body)
    await session.commit()
    await session.refresh(contact, ["company"])
    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID, session: SessionDep, store: ObjectStoreDep, membership: CanWriteCrm
) -> Response:
    """The contact's activities and attachments go with it; tasks are kept, with the
    link cleared."""
    contact = await service.get_contact(session, membership, contact_id)
    await service.delete_contact(session, store, contact)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{contact_id}/activities")
async def list_activities(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[ActivityRead]:
    """Newest first."""
    contact = await service.get_contact(session, membership, contact_id)
    return await paginate(session, service.activities_query(contact), page, ActivityRead)


@router.post("/{contact_id}/activities", status_code=status.HTTP_201_CREATED)
async def create_activity(
    contact_id: UUID, body: ActivityCreate, session: SessionDep, membership: CanWriteCrm
) -> ActivityRead:
    """A call, email, meeting, or follow-up also marks the contact as contacted now."""
    activity = await service.create_activity(session, membership, contact_id, body)
    await session.commit()
    return ActivityRead.model_validate(activity)
