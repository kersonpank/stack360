from __future__ import annotations

from fastapi import APIRouter, Depends

from app.stack360.api.deps import require_ingest
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext
from app.stack360.config import get_settings
from app.stack360.db import get_sessionmaker
from app.stack360.ingestion.gateway import ingest_one
from app.stack360.schemas.envelope import BatchIn, StackEvent
from app.stack360.schemas.errors import ErrorCode, Stack360Error

router = APIRouter(prefix="/ingest", tags=["Ingestion"], route_class=Stack360Route)


def _result_body(res) -> dict:
    body = {"accepted": res.ok, "event_id": res.external_event_id, "status": res.status}
    if res.status == "duplicate":
        body["duplicate"] = True
    if res.status == "processing":
        body["processing"] = True
    if res.entities:
        body["entities"] = res.entities
    if res.resolution_case_id:
        body["resolution_case_id"] = str(res.resolution_case_id)
    if res.error is not None:
        body["error"] = res.error.to_response().model_dump(mode="json")["error"]
    return body


@router.post("/events")
def ingest_event(event: StackEvent, ctx: AuthContext = Depends(require_ingest)):
    Session_ = get_sessionmaker()
    res = ingest_one(Session_, ctx, event, event.model_dump(mode="json"))
    body = _result_body(res)
    if res.status in ("conflict", "error") and res.error is not None:
        # surfacia o código REAL (IDENTITY_CONFLICT / EVENT_ID_CONFLICT / EXPERIENCE_NOT_FOUND / ...)
        err = res.error
        if res.resolution_case_id:
            err = Stack360Error(
                err.code,
                err.message,
                {**err.details, "resolution_case_id": str(res.resolution_case_id)},
            )
        raise err
    return body


@router.post("/events/batch")
def ingest_batch(payload: BatchIn, ctx: AuthContext = Depends(require_ingest)):
    limit = get_settings().batch_max
    if len(payload.events) > limit:
        raise Stack360Error(
            ErrorCode.VALIDATION_ERROR, f"batch excede o limite de {limit} eventos"
        )
    Session_ = get_sessionmaker()
    results = []
    for ev in payload.events:
        res = ingest_one(Session_, ctx, ev, ev.model_dump(mode="json"))
        item = {"event_id": res.external_event_id, "status": res.status}
        if res.entities:
            item["entities"] = res.entities
        if res.resolution_case_id:
            item["resolution_case_id"] = str(res.resolution_case_id)
        if res.error is not None:
            item["error"] = res.error.to_response().model_dump(mode="json")["error"]
        results.append(item)
    return {"results": results}
