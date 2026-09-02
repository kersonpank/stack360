from __future__ import annotations

from fastapi import APIRouter

from app.stack360.api.errors import Stack360Route

router = APIRouter(tags=["Health"], route_class=Stack360Route)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "stack360-core"}
