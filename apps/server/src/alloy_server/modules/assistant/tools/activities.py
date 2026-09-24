import uuid

from pydantic_ai import RunContext
from sqlalchemy import select

from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.tools.common import (
    activity_row,
    check_bulk,
    count_rows,
    next_page,
    owned,
    owned_all,
    page_bounds,
    pause_for_approval,
    plural,
    short,
    write_allowed,
)
from alloy_server.modules.assistant.tools.registry import read_tool, retry, write_tool
from alloy_server.modules.assistant.tools.shapes import ActivityItem, ActivityRow, Page
from alloy_server.modules.crm.contacts import service as contact_service
from alloy_server.modules.crm.contacts.models import Activity, ActivityType, Contact
from alloy_server.modules.crm.contacts.schemas import ActivityCreate
from alloy_server.modules.crm.models import RowSource


@read_tool
async def list_activities(
    ctx: RunContext[AgentDeps], *, contact_id: uuid.UUID, page: int = 1
) -> Page[ActivityRow]:
    """A contact's activity feed, newest first: calls, emails, meetings, notes,
    follow-ups, and completed tasks.

    Args:
        contact_id: The contact.
        page: 1-based page of 20.
    """
    if page < 1:
        raise retry("page starts at 1.")
    deps = ctx.deps
    contact = await owned(deps, Contact, contact_id)
    query = (
        select(Activity)
        .where(Activity.contact_id == contact.id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
    )
    total = await count_rows(deps.session, query)
    limit, offset = page_bounds(page)
    items = [activity_row(a) for a in await deps.session.scalars(query.limit(limit).offset(offset))]
    return Page(items=items, total=total, page=page, next_page=next_page(page, len(items), total))


@write_tool
async def log_activities(
    ctx: RunContext[AgentDeps], items: list[ActivityItem]
) -> list[ActivityRow]:
    """Log a call, email, meeting, note, or follow-up on contacts. A call, email,
    meeting, or follow-up also marks the contact as contacted now. One item runs at
    once; more than one pauses for approval."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    if any(item.type is ActivityType.TASK_COMPLETED for item in items):
        raise retry("task_completed is logged by completing a task with update_tasks.")
    contacts = await owned_all(deps, Contact, [item.contact_id for item in items])
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Log {plural(len(items), 'activity')}".replace("activitys", "activities"),
            columns=["Contact", "Type", "Notes"],
            rows=[
                [contact.name, item.type.value, short(item.notes)]
                for contact, item in zip(contacts, items, strict=True)
            ],
        )
    logged = [
        await contact_service.create_activity(
            deps.session,
            deps.membership,
            item.contact_id,
            ActivityCreate(type=item.type, notes=item.notes),
            source=RowSource.AGENT,
        )
        for item in items
    ]
    await deps.session.commit()
    return [activity_row(a) for a in logged]
