from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from alloy_api.auth.deps import CurrentUserDep
from alloy_api.crm.dates import UTC_ZONE, DueFilter, TimeZoneField, due_clause
from alloy_api.crm.models import Contact, Task, TaskStatus
from alloy_api.crm.schemas import ContactRead, Dashboard
from alloy_api.db import SessionDep
from alloy_api.models import utcnow

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardOptions(BaseModel):
    tz: TimeZoneField = UTC_ZONE
    stale_days: int = Field(30, ge=1, description="Days without contact that count as stale.")
    limit: int = Field(5, ge=1, le=50, description="Size of each contact list.")


@router.get("/")
async def read_dashboard(
    session: SessionDep, user: CurrentUserDep, options: Annotated[DashboardOptions, Query()]
) -> Dashboard:
    """Counts of open tasks due today and overdue, plus who was and was not contacted lately."""
    own_contacts = select(Contact).where(Contact.user_id == user.id)
    open_tasks = select(func.count(Task.id)).where(
        Task.user_id == user.id, Task.status == TaskStatus.OPEN
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
