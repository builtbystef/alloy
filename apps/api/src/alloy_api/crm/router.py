from fastapi import APIRouter

from alloy_api.crm import attachments, companies, contacts, dashboard, tasks

# Every CRM route lives under a workspace; `{workspace_id}` is consumed by the
# membership dependency in alloy_api.workspaces.deps.
router = APIRouter(prefix="/workspaces/{workspace_id}")
router.include_router(companies.router)
router.include_router(contacts.router)
router.include_router(tasks.router)
router.include_router(dashboard.router)
router.include_router(attachments.router)
