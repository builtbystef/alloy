from pydantic import BaseModel, Field

from alloy_server.crm.contacts.schemas import ContactResponse
from alloy_server.crm.dates import UTC_ZONE, TimeZoneField


class DashboardOptions(BaseModel):
    tz: TimeZoneField = UTC_ZONE
    stale_days: int = Field(30, ge=1, description="Days without contact that count as stale.")
    limit: int = Field(5, ge=1, le=50, description="Size of each contact list.")


class DashboardResponse(BaseModel):
    total_contacts: int
    tasks_due_today: int
    overdue_tasks: int
    recently_contacted: list[ContactResponse]
    not_recently_contacted: list[ContactResponse]
