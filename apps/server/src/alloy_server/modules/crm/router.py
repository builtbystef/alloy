from fastapi import APIRouter

from alloy_server.modules.crm.attachments.router import router as attachments_router
from alloy_server.modules.crm.companies.router import router as companies_router
from alloy_server.modules.crm.contacts.router import router as contacts_router
from alloy_server.modules.crm.dashboard.router import router as dashboard_router
from alloy_server.modules.crm.imports.router import router as imports_router
from alloy_server.modules.crm.tasks.router import router as tasks_router

# Every CRM route lives under a workspace; `{workspace_id}` is consumed by the
# membership dependency in alloy_server.modules.workspaces.dependencies.
router = APIRouter(prefix="/workspaces/{workspace_id}")
router.include_router(companies_router)
router.include_router(contacts_router)
router.include_router(tasks_router)
router.include_router(dashboard_router)
router.include_router(attachments_router)
router.include_router(imports_router)
