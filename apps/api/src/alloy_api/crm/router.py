from fastapi import APIRouter

from alloy_api.crm import companies, contacts, dashboard, tasks

router = APIRouter()
router.include_router(companies.router)
router.include_router(contacts.router)
router.include_router(tasks.router)
router.include_router(dashboard.router)
