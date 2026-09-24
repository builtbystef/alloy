from typing import Annotated

from fastapi import APIRouter, Query

from alloy_server.crm.dashboard import service
from alloy_server.crm.dashboard.schemas import DashboardOptions, DashboardResponse
from alloy_server.db.session import SessionDep
from alloy_server.workspaces.deps import CanReadCrm

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def read_dashboard(
    session: SessionDep, membership: CanReadCrm, options: Annotated[DashboardOptions, Query()]
) -> DashboardResponse:
    """Counts of open tasks due today and overdue, plus who was and was not contacted lately."""
    return await service.read_dashboard(session, membership, options)
