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
from app.stack360.models.person import Person, PersonIdentity, WorkspacePerson
from app.stack360.resolution.normalize import normalize_identity
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.services.context import person_context

router = APIRouter(prefix="/people", tags=["People"], route_class=Stack360Route)


@router.get("")
def list_people(
    query: Optional[str] = Query(default=None),
    identity_type: Optional[str] = Query(default=None),
    identity_value: Optional[str] = Query(default=None),
    page: PageParams = Depends(),
    ctx: AuthContext = Depends(require_read),
    db: Session = Depends(db_session),
):
    stmt = (
        select(Person)
        .join(WorkspacePerson, WorkspacePerson.person_id == Person.id)
        .where(WorkspacePerson.workspace_id == ctx.workspace_id)
    )
    if query:
        stmt = stmt.where(Person.canonical_name.ilike(f"%{query}%"))
    if identity_type and identity_value:
        ni = normalize_identity(identity_type, identity_value, has_data_source=True)
        if ni is None:
            raise Stack360Error(ErrorCode.VALIDATION_ERROR, "identity_value inválido")
        stmt = stmt.join(PersonIdentity, PersonIdentity.person_id == Person.id).where(
            PersonIdentity.identity_type == ni.identity_type,
            PersonIdentity.value_hash == ni.value_hash,
        )
    if page.cursor:
        _, last_id = page.cursor
        stmt = stmt.where(Person.id > uuid.UUID(last_id))
    rows = db.execute(stmt.order_by(Person.id).limit(page.limit + 1)).scalars().all()
    has_more = len(rows) > page.limit
    rows = rows[: page.limit]
    return {
        "items": [
            {"id": str(p.id), "canonical_name": p.canonical_name, "created_at": p.created_at}
            for p in rows
        ],
        "next_cursor": encode_cursor(rows[-1].id, rows[-1].id) if (has_more and rows) else None,
    }


@router.get("/{person_id}")
def get_person(person_id: uuid.UUID, ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    from app.stack360.services.context import get_person_or_404

    p = get_person_or_404(db, ctx.workspace_id, person_id)
    return {"id": str(p.id), "canonical_name": p.canonical_name, "created_at": p.created_at}


@router.get("/{person_id}/context")
def get_person_context(
    person_id: uuid.UUID,
    limit: Optional[int] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    include: Optional[str] = Query(default=None),
    ctx: AuthContext = Depends(require_read),
    db: Session = Depends(db_session),
):
    return person_context(db, ctx.workspace_id, person_id, limit=limit, since=since, include=include)
