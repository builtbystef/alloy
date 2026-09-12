from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_api.crm.contacts.models import Contact
from alloy_api.crm.contacts.schemas import ContactRead
from alloy_api.crm.dashboard.schemas import Dashboard
from alloy_api.crm.dates import DueFilter, due_clause
from alloy_api.crm.tasks.models import Task, TaskStatus
from alloy_api.db.base import utcnow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.crm.dashboard.schemas import DashboardOptions
    from alloy_api.workspaces.deps import Membership


async def read_dashboard(
    session: AsyncSession, membership: Membership, options: DashboardOptions
) -> Dashboard:
    own_contacts = select(Contact).where(Contact.workspace_id == membership.workspace.id)
    open_tasks = select(func.count(Task.id)).where(
        Task.workspace_id == membership.workspace.id, Task.status == TaskStatus.OPEN
    )
    stale_before = utcnow() - timedelta(days=options.stale_days)

    total_contacts = await session.scalar(select(func.count()).select_from(own_contacts.subquery()))
    tasks_due_today = await session.scalar(
        open_tasks.where(due_clause(Task.due_at, DueFilter.TODAY, options.tz))
    )
    overdue_tasks = await session.scalar(
        open_tasks.where(due_clause(Task.due_at, DueFilter.OVERDUE, options.tz))
    )
    recently_contacted = await session.scalars(
        own_contacts.options(selectinload(Contact.company))
        .where(Contact.last_contacted_at.is_not(None))
        .order_by(Contact.last_contacted_at.desc(), Contact.id)
        .limit(options.limit)
    )
    not_recently_contacted = await session.scalars(
        own_contacts.options(selectinload(Contact.company))
        .where(Contact.last_contacted_at.is_(None) | (Contact.last_contacted_at < stale_before))
        .order_by(Contact.last_contacted_at.desc().nulls_last(), Contact.id)
        .limit(options.limit)
    )
    return Dashboard(
        total_contacts=total_contacts or 0,
        tasks_due_today=tasks_due_today or 0,
        overdue_tasks=overdue_tasks or 0,
        recently_contacted=[ContactRead.model_validate(c) for c in recently_contacted],
        not_recently_contacted=[ContactRead.model_validate(c) for c in not_recently_contacted],
    )
