from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_api.auth.deps import CurrentUserDep
from alloy_api.crm.common import Page, check_owned, fetch_owned
from alloy_api.crm.dates import UTC_ZONE, DueFilter, TimeZoneField, due_clause
from alloy_api.crm.models import Activity, ActivityType, Company, Contact, Task, TaskStatus
from alloy_api.crm.schemas import TaskCreate, TaskRead, TaskUpdate
from alloy_api.db import SessionDep
from alloy_api.models import utcnow

router = APIRouter(prefix="/tasks", tags=["tasks"])

WITH_RELATIONS = (selectinload(Task.contact), selectinload(Task.company))


class TaskFilters(Page):
    """`due` and `status` filter independently: pass both for open overdue tasks."""

    due: DueFilter | None = None
    tz: TimeZoneField = UTC_ZONE
    status: TaskStatus | None = None
    contact_id: UUID | None = None
    company_id: UUID | None = None


@router.get("/")
async def list_tasks(
    session: SessionDep, user: CurrentUserDep, filters: Annotated[TaskFilters, Query()]
) -> list[TaskRead]:
    """Soonest due first, undated last."""
    query = select(Task).options(*WITH_RELATIONS).where(Task.user_id == user.id)
    if filters.due is not None:
        query = query.where(due_clause(Task.due_at, filters.due, filters.tz))
    if filters.status is not None:
        query = query.where(Task.status == filters.status)
    if filters.contact_id is not None:
        query = query.where(Task.contact_id == filters.contact_id)
    if filters.company_id is not None:
        query = query.where(Task.company_id == filters.company_id)
    query = (
        query.order_by(Task.due_at.asc().nulls_last(), Task.created_at, Task.id)
        .limit(filters.limit)
        .offset(filters.offset)
    )
    return [TaskRead.model_validate(t) for t in await session.scalars(query)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, session: SessionDep, user: CurrentUserDep) -> TaskRead:
    await check_owned(session, Contact, body.contact_id, user)
    await check_owned(session, Company, body.company_id, user)
    task = Task(user_id=user.id, **body.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task, ["contact", "company"])
    return TaskRead.model_validate(task)


@router.get("/{task_id}")
async def read_task(task_id: UUID, session: SessionDep, user: CurrentUserDep) -> TaskRead:
    return TaskRead.model_validate(await fetch_owned(session, Task, task_id, user, *WITH_RELATIONS))


@router.patch("/{task_id}")
async def update_task(
    task_id: UUID, body: TaskUpdate, session: SessionDep, user: CurrentUserDep
) -> TaskRead:
    """Marking a task done logs a `task_completed` activity on its contact."""
    task = await fetch_owned(session, Task, task_id, user)
    changes = body.model_dump(exclude_unset=True)
    if "contact_id" in changes:
        await check_owned(session, Contact, changes["contact_id"], user)
    if "company_id" in changes:
        await check_owned(session, Company, changes["company_id"], user)
    completed = task.status != TaskStatus.DONE and changes.get("status") == TaskStatus.DONE
    for field, value in changes.items():
        setattr(task, field, value)
    if completed and task.contact_id is not None:
        session.add(
            Activity(
                contact_id=task.contact_id,
                type=ActivityType.TASK_COMPLETED,
                notes=task.title,
                created_at=utcnow(),
            )
        )
    await session.commit()
    await session.refresh(task, ["contact", "company"])
    return TaskRead.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, session: SessionDep, user: CurrentUserDep) -> Response:
    task = await fetch_owned(session, Task, task_id, user)
    await session.delete(task)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
