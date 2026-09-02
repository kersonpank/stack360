from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.stack360.api.deps import db_session, require_read
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext
from app.stack360.base import utcnow
from app.stack360.models.data_source import DataSource, SourceSyncState
from app.stack360.models.ingestion_event import IngestionEvent

router = APIRouter(prefix="/sources", tags=["Sources"], route_class=Stack360Route)


@router.get("")
def list_sources(ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    rows = db.execute(
        select(DataSource).where(DataSource.workspace_id == ctx.workspace_id).order_by(DataSource.key)
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(s.id),
                "key": s.key,
                "name": s.name,
                "source_type": s.source_type,
                "status": s.status,
            }
            for s in rows
        ]
    }


@router.get("/health")
def sources_health(ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    sources = db.execute(
        select(DataSource).where(DataSource.workspace_id == ctx.workspace_id).order_by(DataSource.key)
    ).scalars().all()
    day_ago = utcnow() - timedelta(hours=24)
    out = []
    for s in sources:
        sync = db.get(SourceSyncState, s.id)
        last_event = db.execute(
            select(func.max(IngestionEvent.received_at)).where(IngestionEvent.data_source_id == s.id)
        ).scalar_one_or_none()
        events_24h = db.execute(
            select(func.count()).select_from(IngestionEvent).where(
                IngestionEvent.data_source_id == s.id, IngestionEvent.received_at >= day_ago
            )
        ).scalar_one()
        failed_24h = db.execute(
            select(func.count()).select_from(IngestionEvent).where(
                IngestionEvent.data_source_id == s.id,
                IngestionEvent.received_at >= day_ago,
                IngestionEvent.status.in_(("failed", "conflict")),
            )
        ).scalar_one()
        out.append(
            {
                "source_key": s.key,
                "name": s.name,
                "status": s.status,
                "last_event_at": last_event,
                "last_success_at": sync.last_success_at if sync else None,
                "last_error_at": sync.last_error_at if sync else None,
                "last_error_message": sync.last_error_message if sync else None,
                "events_24h": events_24h,
                "failed_24h": failed_24h,
                "feeding": bool(last_event and last_event >= day_ago),
            }
        )
    return {"items": out}
