from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.api.deps import db_session, require_read
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext
from app.stack360.models.data_source import DataSource
from app.stack360.models.resolution import ResolutionCase, ResolutionRecommendation
from app.stack360.schemas.errors import ErrorCode, Stack360Error

router = APIRouter(prefix="/resolution-cases", tags=["Resolution"], route_class=Stack360Route)


def _case_dict(c: ResolutionCase) -> dict:
    return {
        "id": str(c.id),
        "case_type": c.case_type,
        "status": c.status,
        "severity": c.severity,
        "subject_type": c.subject_type,
        "subject_id": str(c.subject_id) if c.subject_id else None,
        "ingestion_event_id": str(c.ingestion_event_id) if c.ingestion_event_id else None,
        "details": c.details,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "resolved_at": c.resolved_at,
        "resolved_by_type": c.resolved_by_type,
        "resolution_action": c.resolution_action,
    }


@router.get("")
def list_cases(
    status: Optional[str] = Query(default=None),
    case_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    created_since: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, le=200),
    ctx: AuthContext = Depends(require_read),
    db: Session = Depends(db_session),
):
    stmt = select(ResolutionCase).where(ResolutionCase.workspace_id == ctx.workspace_id)
    if status:
        stmt = stmt.where(ResolutionCase.status == status)
    if case_type:
        stmt = stmt.where(ResolutionCase.case_type == case_type)
    if severity:
        stmt = stmt.where(ResolutionCase.severity == severity)
    if created_since:
        stmt = stmt.where(ResolutionCase.created_at >= created_since)
    if source:
        ds = db.execute(
            select(DataSource.id).where(
                DataSource.workspace_id == ctx.workspace_id, DataSource.key == source
            )
        ).scalar_one_or_none()
        from app.stack360.models.ingestion_event import IngestionEvent

        stmt = stmt.join(
            IngestionEvent, IngestionEvent.id == ResolutionCase.ingestion_event_id
        ).where(IngestionEvent.data_source_id == ds)
    rows = db.execute(stmt.order_by(ResolutionCase.created_at.desc()).limit(limit)).scalars().all()
    return {"items": [_case_dict(c) for c in rows]}


@router.get("/{case_id}")
def get_case(case_id: uuid.UUID, ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    c = db.get(ResolutionCase, case_id)
    if c is None or c.workspace_id != ctx.workspace_id:
        raise Stack360Error(ErrorCode.NOT_FOUND, "resolution_case não encontrado")
    recs = db.execute(
        select(ResolutionRecommendation)
        .where(ResolutionRecommendation.resolution_case_id == case_id)
        .order_by(ResolutionRecommendation.created_at.desc())
    ).scalars().all()
    body = _case_dict(c)
    body["recommendations"] = [
        {
            "id": str(r.id),
            "recommended_action": r.recommended_action,
            "candidate_entity_ids": r.candidate_entity_ids,
            "confidence": float(r.confidence) if r.confidence is not None else None,
            "evidence": r.evidence,
            "summary": r.summary,
            "agent_name": r.agent_name,
            "agent_version": r.agent_version,
            "created_at": r.created_at,
        }
        for r in recs
    ]
    return body
