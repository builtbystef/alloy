from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated
from zoneinfo import ZoneInfo

from pydantic import Field

from alloy_api.models import utcnow

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import InstrumentedAttribute

TimeZoneField = Annotated[ZoneInfo, Field(description="IANA time zone that defines 'today'.")]
UTC_ZONE = ZoneInfo("UTC")


class DueFilter(StrEnum):
    OVERDUE = "overdue"
    TODAY = "today"
    UPCOMING = "upcoming"


def today_bounds(zone: ZoneInfo) -> tuple[datetime, datetime]:
    """Start of today and start of tomorrow in `zone`, as aware datetimes."""
    start = utcnow().astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def due_clause(
    due_at: InstrumentedAttribute[datetime | None], due: DueFilter, zone: ZoneInfo
) -> ColumnElement[bool]:
    """Overdue is before today, upcoming is after it; undated rows match neither."""
    start, end = today_bounds(zone)
    match due:
        case DueFilter.OVERDUE:
            return due_at < start
        case DueFilter.TODAY:
            return (due_at >= start) & (due_at < end)
        case DueFilter.UPCOMING:
            return due_at >= end
