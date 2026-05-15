from fastapi import APIRouter

from app.api.v1.endpoints import conversations, health, stakeholders

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(stakeholders.router)
router.include_router(conversations.router)
