from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from alloy_server.crm.pagination import PageOf, paginate
from alloy_server.crm.tasks import service
from alloy_server.crm.tasks.schemas import TaskCreate, TaskFilters, TaskResponse, TaskUpdate
from alloy_server.db.session import SessionDep
from alloy_server.workspaces.dependencies import CanReadCrm, CanWriteCrm

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/")
async def list_tasks(
    session: SessionDep, membership: CanReadCrm, filters: Annotated[TaskFilters, Query()]
) -> PageOf[TaskResponse]:
    """Soonest due first unless `sort` says otherwise; tasks without a value for the
    sort column (undated, or with no contact or company) come last either way."""
    return await paginate(session, service.tasks_query(membership, filters), filters, TaskResponse)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate, session: SessionDep, membership: CanWriteCrm
) -> TaskResponse:
    task = await service.create_task(session, membership, body)
    await session.commit()
    await service.load_relations(session, task)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}")
async def read_task(task_id: UUID, session: SessionDep, membership: CanReadCrm) -> TaskResponse:
    return TaskResponse.model_validate(await service.get_task(session, membership, task_id))


@router.patch("/{task_id}")
async def update_task(
    task_id: UUID, body: TaskUpdate, session: SessionDep, membership: CanWriteCrm
) -> TaskResponse:
    """Marking a task done logs a `task_completed` activity on its contact."""
    task = await service.update_task(session, membership, task_id, body)
    await session.commit()
    await service.load_relations(session, task)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, session: SessionDep, membership: CanWriteCrm) -> Response:
    await service.delete_task(session, membership, task_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
