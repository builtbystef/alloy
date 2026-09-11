from typing import TYPE_CHECKING

from sqlalchemy import select

from alloy_api.crm.common import check_owned, fetch_owned
from alloy_api.crm.models import (
    CONTACT_ACTIVITY_TYPES,
    Activity,
    ActivityType,
    Attachment,
    Company,
    Contact,
    RowSource,
    Task,
    TaskStatus,
)
from alloy_api.models import utcnow
from alloy_api.storage.cleanup import delete_stored

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.crm.schemas import (
        ActivityCreate,
        CompanyCreate,
        CompanyUpdate,
        ContactCreate,
        ContactUpdate,
        TaskCreate,
        TaskUpdate,
    )
    from alloy_api.storage import ObjectStore
    from alloy_api.workspaces.deps import Membership


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
    contact = await fetch_owned(session, Contact, contact_id, membership)
    changes = body.model_dump(exclude_unset=True)
    if "company_id" in changes:
        await check_owned(session, Company, changes["company_id"], membership)
    for field, value in changes.items():
        setattr(contact, field, value)
    await session.flush()
    return contact


async def delete_with_objects(
    session: AsyncSession, store: ObjectStore, parent: Contact | Company
) -> None:
    """Delete a contact or company and commit, then remove the stored files of the
    attachments that went with it."""
    column = Attachment.contact_id if isinstance(parent, Contact) else Attachment.company_id
    keys = list(await session.scalars(select(Attachment.key).where(column == parent.id)))
    await session.delete(parent)
    await session.commit()
    await delete_stored(store, keys=keys)


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


async def create_task(
    session: AsyncSession,
    membership: Membership,
    body: TaskCreate,
    *,
    source: RowSource | None = None,
) -> Task:
    await check_owned(session, Contact, body.contact_id, membership)
    await check_owned(session, Company, body.company_id, membership)
    task = Task(
        workspace_id=membership.workspace.id,
        created_by=membership.user,
        source=source,
        **body.model_dump(),
    )
    session.add(task)
    await session.flush()
    return task


async def update_task(
    session: AsyncSession,
    membership: Membership,
    task_id: UUID,
    body: TaskUpdate,
    *,
    source: RowSource | None = None,
) -> Task:
    """Marking a task done logs a `task_completed` activity on its contact."""
    task = await fetch_owned(session, Task, task_id, membership)
    changes = body.model_dump(exclude_unset=True)
    if "contact_id" in changes:
        await check_owned(session, Contact, changes["contact_id"], membership)
    if "company_id" in changes:
        await check_owned(session, Company, changes["company_id"], membership)
    completed = task.status != TaskStatus.DONE and changes.get("status") == TaskStatus.DONE
    for field, value in changes.items():
        setattr(task, field, value)
    if completed and task.contact_id is not None:
        session.add(
            Activity(
                contact_id=task.contact_id,
                type=ActivityType.TASK_COMPLETED,
                notes=task.title,
                created_by=membership.user,
                source=source,
                created_at=utcnow(),
            )
        )
    await session.flush()
    return task


async def delete_task(session: AsyncSession, membership: Membership, task_id: UUID) -> Task:
    task = await fetch_owned(session, Task, task_id, membership)
    await session.delete(task)
    await session.flush()
    return task


async def delete_attachment(
    session: AsyncSession, store: ObjectStore, membership: Membership, attachment_id: UUID
) -> Attachment:
    """Removes the row and commits, then the file from the store."""
    attachment = await fetch_owned(session, Attachment, attachment_id, membership)
    await session.delete(attachment)
    await session.commit()
    await delete_stored(store, keys=[attachment.key])
    return attachment
