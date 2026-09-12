from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

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

WITH_RELATIONS = (selectinload(Task.contact), selectinload(Task.company))

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
    if filters.sort is TaskSort.CONTACT:
        query = query.outerjoin(Task.contact)
    elif filters.sort is TaskSort.COMPANY:
        query = query.outerjoin(Task.company)
    if filters.due is not None:
        query = query.where(due_clause(Task.due_at, filters.due, filters.tz))
    if filters.status is not None:
        query = query.where(Task.status == filters.status)
    if filters.contact_id is not None:
        query = query.where(Task.contact_id == filters.contact_id)
    if filters.company_id is not None:
        query = query.where(Task.company_id == filters.company_id)
    return sorted_by(query, SORT_COLUMNS[filters.sort], filters.order, Task.id)


async def get_task(session: AsyncSession, membership: Membership, task_id: UUID) -> Task:
    return await fetch_owned(session, Task, task_id, membership, *WITH_RELATIONS)


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
