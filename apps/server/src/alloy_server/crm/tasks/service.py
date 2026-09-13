from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_server.core.exceptions import ConflictError
from alloy_server.crm.companies.models import Company
from alloy_server.crm.contacts.models import Activity, ActivityType, Contact
from alloy_server.crm.dates import due_clause
from alloy_server.crm.ownership import check_owned, fetch_owned
from alloy_server.crm.pagination import sorted_by
from alloy_server.crm.tasks.models import Task, TaskStatus
from alloy_server.crm.tasks.schemas import TaskSort
from alloy_server.db.base import utcnow

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.crm.models import RowSource
    from alloy_server.crm.tasks.schemas import TaskCreate, TaskFilters, TaskUpdate
    from alloy_server.workspaces.deps import Membership

# `contact.company` too, for `Task.linked_company`.
WITH_RELATIONS = (
    selectinload(Task.contact).selectinload(Contact.company),
    selectinload(Task.company),
)

# `Task.linked_company` in SQL. Valid once the query has joined `Task.contact`.
linked_company_id = func.coalesce(Task.company_id, Contact.company_id)

SORT_COLUMNS = {
    TaskSort.DUE_AT: Task.due_at,
    TaskSort.TITLE: Task.title,
    TaskSort.CONTACT: Contact.name,
    TaskSort.COMPANY: Company.name,
}


def tasks_query(membership: Membership, filters: TaskFilters) -> Select[tuple[Task]]:
    """The workspace's tasks, filtered and sorted. Shared with the assistant."""
    query = (
        select(Task).options(*WITH_RELATIONS).where(Task.workspace_id == membership.workspace.id)
    )
    by_company = filters.sort is TaskSort.COMPANY or filters.company_id is not None
    if filters.sort is TaskSort.CONTACT or by_company:
        query = query.outerjoin(Task.contact)
    if filters.sort is TaskSort.COMPANY:
        query = query.outerjoin(Company, Company.id == linked_company_id)
    if filters.due is not None:
        query = query.where(due_clause(Task.due_at, filters.due, filters.tz))
    if filters.status is not None:
        query = query.where(Task.status == filters.status)
    if filters.contact_id is not None:
        query = query.where(Task.contact_id == filters.contact_id)
    if filters.company_id is not None:
        query = query.where(linked_company_id == filters.company_id)
    return sorted_by(query, SORT_COLUMNS[filters.sort], filters.order, Task.id)


async def load_relations(session: AsyncSession, task: Task) -> None:
    """Fresh `contact`, `company`, and `contact.company` after a commit expired them."""
    await session.refresh(task, ["contact", "company"])
    if task.contact is not None:
        await session.refresh(task.contact, ["company"])


async def check_links(
    session: AsyncSession, membership: Membership, contact_id: UUID | None, company_id: UUID | None
) -> None:
    """One link, in the caller's workspace."""
    if contact_id is not None and company_id is not None:
        raise ConflictError("A task is linked to a contact or a company, not both")
    await check_owned(session, Contact, contact_id, membership)
    await check_owned(session, Company, company_id, membership)


async def get_task(session: AsyncSession, membership: Membership, task_id: UUID) -> Task:
    return await fetch_owned(session, Task, task_id, membership, *WITH_RELATIONS)


async def create_task(
    session: AsyncSession,
    membership: Membership,
    body: TaskCreate,
    *,
    source: RowSource | None = None,
) -> Task:
    await check_links(session, membership, body.contact_id, body.company_id)
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
    await check_links(session, membership, changes.get("contact_id"), changes.get("company_id"))
    # The link moves: a new contact replaces a company, and the other way round.
    if changes.get("contact_id") is not None:
        changes["company_id"] = None
    if changes.get("company_id") is not None:
        changes["contact_id"] = None
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
