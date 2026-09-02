from __future__ import annotations

from fastapi import APIRouter

from app.stack360.api import (
    companies,
    experiences,
    health,
    ingest,
    interactions,
    people,
    resolution_cases,
    sources,
    webhooks,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(ingest.router)
router.include_router(webhooks.router)
router.include_router(people.router)
router.include_router(companies.router)
router.include_router(interactions.router)
router.include_router(experiences.router)
router.include_router(sources.router)
router.include_router(resolution_cases.router)
