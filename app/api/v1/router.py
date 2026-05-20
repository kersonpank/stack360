from fastapi import APIRouter

from app.api.v1.endpoints import actions, conversations, health, stakeholders, system

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(stakeholders.router)
router.include_router(conversations.router)
router.include_router(system.router)
router.include_router(actions.router)
