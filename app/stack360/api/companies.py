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
from app.stack360.models.company import Company, WorkspaceCompany
from app.stack360.services.context import company_context, get_company_or_404

router = APIRouter(prefix="/companies", tags=["Companies"], route_class=Stack360Route)


@router.get("")
def list_companies(
    query: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    cnpj: Optional[str] = Query(default=None),
    page: PageParams = Depends(),
    ctx: AuthContext = Depends(require_read),
    db: Session = Depends(db_session),
):
    stmt = (
        select(Company)
        .join(WorkspaceCompany, WorkspaceCompany.company_id == Company.id)
        .where(WorkspaceCompany.workspace_id == ctx.workspace_id)
    )
    if query:
        stmt = stmt.where(Company.canonical_name.ilike(f"%{query}%"))
    if domain:
        stmt = stmt.where(Company.domain == domain.lower())
    if cnpj:
        stmt = stmt.where(Company.cnpj_normalized == "".join(ch for ch in cnpj if ch.isdigit()))
    if page.cursor:
        _, last_id = page.cursor
        stmt = stmt.where(Company.id > uuid.UUID(last_id))
    rows = db.execute(stmt.order_by(Company.id).limit(page.limit + 1)).scalars().all()
    has_more = len(rows) > page.limit
    rows = rows[: page.limit]
    return {
        "items": [
            {
                "id": str(c.id),
                "canonical_name": c.canonical_name,
                "domain": c.domain,
                "cnpj_normalized": c.cnpj_normalized,
            }
            for c in rows
        ],
        "next_cursor": encode_cursor(rows[-1].id, rows[-1].id) if (has_more and rows) else None,
    }


@router.get("/{company_id}")
def get_company(company_id: uuid.UUID, ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    c = get_company_or_404(db, ctx.workspace_id, company_id)
    return {
        "id": str(c.id),
        "canonical_name": c.canonical_name,
        "domain": c.domain,
        "cnpj_normalized": c.cnpj_normalized,
        "website": c.website,
        "created_at": c.created_at,
    }


@router.get("/{company_id}/context")
def get_company_context(
    company_id: uuid.UUID,
    limit: Optional[int] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    include: Optional[str] = Query(default=None),
    ctx: AuthContext = Depends(require_read),
    db: Session = Depends(db_session),
):
    return company_context(db, ctx.workspace_id, company_id, limit=limit, since=since, include=include)
