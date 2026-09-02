from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.api.deps import PageParams, db_session, encode_cursor, require_read
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext
from app.stack360.models.data_source import DataSource
from app.stack360.models.interaction import Interaction

router = APIRouter(prefix="/interactions", tags=["Interactions"], route_class=Stack360Route)


@router.get("")
def list_interactions(
    person_id: Optional[uuid.UUID] = Query(default=None),
    company_id: Optional[uuid.UUID] = Query(default=None),
    type: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    page: PageParams = Depends(),
    ctx: AuthContext = Depends(require_read),
    db: Session = Depends(db_session),
):
    stmt = select(Interaction).where(Interaction.workspace_id == ctx.workspace_id)
    if person_id:
        stmt = stmt.where(Interaction.person_id == person_id)
    if company_id:
        stmt = stmt.where(Interaction.company_id == company_id)
    if type:
        stmt = stmt.where(Interaction.interaction_type == type)
    if since:
        stmt = stmt.where(Interaction.occurred_at >= since)
    if page.cursor:
        cur_time, cur_id = page.cursor
        stmt = stmt.where(Interaction.occurred_at < datetime.fromisoformat(cur_time))
    rows = db.execute(
        stmt.order_by(Interaction.occurred_at.desc(), Interaction.id.desc()).limit(page.limit + 1)
    ).scalars().all()
    has_more = len(rows) > page.limit
    rows = rows[: page.limit]
    sk = {r.id: r.key for r in db.execute(select(DataSource)).scalars()}
    return {
        "items": [
            {
                "id": str(r.id),
                "interaction_type": r.interaction_type,
                "channel": r.channel,
                "direction": r.direction,
                "occurred_at": r.occurred_at,
                "person_id": str(r.person_id) if r.person_id else None,
                "company_id": str(r.company_id) if r.company_id else None,
                "data_source_key": sk.get(r.data_source_id),
                "metadata": r.meta,
            }
            for r in rows
        ],
        "next_cursor": encode_cursor(rows[-1].occurred_at.isoformat(), rows[-1].id)
        if (has_more and rows)
        else None,
    }
