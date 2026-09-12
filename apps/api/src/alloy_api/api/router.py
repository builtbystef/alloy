"""Router order is the OpenAPI schema order, which `packages/api-client` is
generated from. Keep it stable."""

from fastapi import APIRouter

from alloy_api.agent.router import router as agent_router
from alloy_api.auth.router import router as auth_router
from alloy_api.crm.router import router as crm_router
from alloy_api.health.router import router as health_router
from alloy_api.workspaces.invites import router as invites_router
from alloy_api.workspaces.router import router as workspaces_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(invites_router)
router.include_router(crm_router)
router.include_router(agent_router)
