import uuid

from pydantic_ai import RunContext
from sqlalchemy.orm import selectinload

from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.tools.common import (
    check_bulk,
    count_rows,
    next_page,
    owned_all,
    page_bounds,
    pause_for_approval,
    plural,
    short,
    task_row,
    write_allowed,
)
from alloy_server.modules.assistant.tools.registry import (
    approval_tool,
    read_tool,
    retry,
    write_tool,
)
from alloy_server.modules.assistant.tools.shapes import Deleted, Page, TaskChange, TaskRow
from alloy_server.modules.crm.dates import DueFilter
from alloy_server.modules.crm.models import RowSource
from alloy_server.modules.crm.tasks import service as task_service
from alloy_server.modules.crm.tasks.models import Task, TaskStatus
from alloy_server.modules.crm.tasks.schemas import TaskCreate, TaskFilters


@read_tool
async def list_tasks(  # noqa: PLR0913
    ctx: RunContext[AgentDeps],
    *,
    due: DueFilter | None = None,
    status: TaskStatus | None = TaskStatus.OPEN,
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    page: int = 1,
) -> Page[TaskRow]:
    """Tasks, soonest due first. "Today" follows the user's time zone.

    Args:
        due: `overdue` (before today), `today`, or `upcoming` (after today). Undated
            tasks match none of these.
        status: `open` (the default) or `done`; null for both.
        contact_id: Only tasks linked to this contact.
        company_id: Only tasks linked to this company, or to one of its contacts.
        page: 1-based page of 20.
    """
    if page < 1:
        raise retry("page starts at 1.")
    deps = ctx.deps
    filters = TaskFilters(
        due=due, tz=deps.time_zone, status=status, contact_id=contact_id, company_id=company_id
    )
    query = task_service.tasks_query(deps.membership, filters)
    total = await count_rows(deps.session, query)
    limit, offset = page_bounds(page)
    items = [
        task_row(deps, t) for t in await deps.session.scalars(query.limit(limit).offset(offset))
    ]
    return Page(items=items, total=total, page=page, next_page=next_page(page, len(items), total))


@write_tool
async def create_tasks(ctx: RunContext[AgentDeps], items: list[TaskCreate]) -> list[TaskRow]:
    """Create tasks. `due_at` is an ISO 8601 datetime with a time zone offset: work out
    "next Tuesday" or "in two weeks" from today's date and the user's time zone, using
    09:00 when no time is given. A task links to a contact or a company, not both: a
    task about a person at a company links to the person. One item runs at once; more
    than one pauses for approval."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Create {plural(len(items), 'task')}",
            columns=["Title", "Due"],
            rows=[[item.title, item.due_at.isoformat() if item.due_at else ""] for item in items],
        )
    created = [
        await task_service.create_task(deps.session, deps.membership, item, source=RowSource.AGENT)
        for item in items
    ]
    await deps.session.commit()
    for task in created:
        await task_service.load_relations(deps.session, task)
    return [task_row(deps, t) for t in created]


@write_tool
async def update_tasks(ctx: RunContext[AgentDeps], items: list[TaskChange]) -> list[TaskRow]:
    """Change tasks, including completing (`status: done`) and reopening them. One
    item runs at once; more than one pauses for approval."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    tasks = await owned_all(deps, Task, [item.task_id for item in items])
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Update {plural(len(items), 'task')}",
            columns=["Task", "Changes"],
            rows=[
                [task.title, short(item.changes.model_dump(exclude_unset=True), 80)]
                for task, item in zip(tasks, items, strict=True)
            ],
        )
    updated = [
        await task_service.update_task(
            deps.session, deps.membership, item.task_id, item.changes, source=RowSource.AGENT
        )
        for item in items
    ]
    await deps.session.commit()
    for task in updated:
        await task_service.load_relations(deps.session, task)
    return [task_row(deps, t) for t in updated]


@approval_tool
async def delete_tasks(ctx: RunContext[AgentDeps], task_ids: list[uuid.UUID]) -> Deleted:
    """Delete tasks. Always pauses for the user's approval."""
    write_allowed(ctx)
    deps = ctx.deps
    tasks = await owned_all(deps, Task, task_ids, selectinload(Task.contact))
    await pause_for_approval(
        ctx,
        title=f"Delete {plural(len(tasks), 'task')}",
        columns=["Title", "Contact", "Due"],
        rows=[
            [t.title, t.contact.name if t.contact else "", t.due_at.isoformat() if t.due_at else ""]
            for t in tasks
        ],
    )
    titles = [t.title for t in tasks]
    for task in tasks:
        await task_service.delete_task(deps.session, deps.membership, task.id)
    await deps.session.commit()
    return Deleted(deleted=titles)
