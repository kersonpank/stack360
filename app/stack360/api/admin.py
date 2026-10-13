"""Gestão de workspace/source/api-key via REST — equivalente do admin.py CLI.

Tudo atrás de ``require_admin`` (scope ``admin``). A key com esse scope é
bootstrap único via CLI (``create-api-key --scopes admin``) e fica só no
servidor do dashboard — nunca chega ao browser.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.stack360.api.deps import db_session, require_admin
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext
from app.stack360.base import utcnow
from app.stack360.models.api_key import ApiKey
from app.stack360.models.data_source import DataSource
from app.stack360.models.workspace import Workspace
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.security.hashing import generate_api_key

router = APIRouter(prefix="/admin", tags=["Admin"], route_class=Stack360Route)


class CreateWorkspaceIn(BaseModel):
    slug: str
    name: str


class CreateSourceIn(BaseModel):
    workspace_id: uuid.UUID
    key: str
    name: str
    source_type: str


class CreateApiKeyIn(BaseModel):
    workspace_id: uuid.UUID
    source_id: Optional[uuid.UUID] = None
    name: str
    scopes: list[str]


def _get_workspace_or_404(db: Session, workspace_id: uuid.UUID) -> Workspace:
    w = db.get(Workspace, workspace_id)
    if w is None:
        raise Stack360Error(ErrorCode.NOT_FOUND, "workspace não encontrado")
    return w


@router.get("/workspaces")
def list_workspaces(ctx: AuthContext = Depends(require_admin), db: Session = Depends(db_session)):
    rows = db.execute(select(Workspace).order_by(Workspace.name)).scalars().all()
    return {"items": [{"id": str(w.id), "slug": w.slug, "name": w.name} for w in rows]}


@router.post("/workspaces")
def create_workspace(
    body: CreateWorkspaceIn, ctx: AuthContext = Depends(require_admin), db: Session = Depends(db_session)
):
    w = Workspace(slug=body.slug, name=body.name)
    db.add(w)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Stack360Error(ErrorCode.VALIDATION_ERROR, f"workspace com slug '{body.slug}' já existe")
    return {"id": str(w.id), "slug": w.slug, "name": w.name}


@router.get("/sources")
def list_sources(
    workspace_id: uuid.UUID = Query(...),
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(db_session),
):
    rows = db.execute(
        select(DataSource).where(DataSource.workspace_id == workspace_id).order_by(DataSource.key)
    ).scalars().all()
    return {
        "items": [
            {"id": str(s.id), "key": s.key, "name": s.name, "source_type": s.source_type, "status": s.status}
            for s in rows
        ]
    }


@router.post("/sources")
def create_source(
    body: CreateSourceIn, ctx: AuthContext = Depends(require_admin), db: Session = Depends(db_session)
):
    _get_workspace_or_404(db, body.workspace_id)
    s = DataSource(workspace_id=body.workspace_id, key=body.key, name=body.name, source_type=body.source_type)
    db.add(s)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Stack360Error(
            ErrorCode.VALIDATION_ERROR, f"source com key '{body.key}' já existe nesse workspace"
        )
    return {"id": str(s.id), "key": s.key, "name": s.name, "source_type": s.source_type}


@router.get("/api-keys")
def list_api_keys(
    workspace_id: uuid.UUID = Query(...),
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(db_session),
):
    rows = db.execute(
        select(ApiKey, DataSource.key)
        .join(DataSource, DataSource.id == ApiKey.data_source_id, isouter=True)
        .where(ApiKey.workspace_id == workspace_id)
        .order_by(ApiKey.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "status": k.status,
                "source_key": source_key,
                "created_at": k.created_at,
                "last_used_at": k.last_used_at,
            }
            for k, source_key in rows
        ]
    }


@router.post("/api-keys")
def create_api_key(
    body: CreateApiKeyIn, ctx: AuthContext = Depends(require_admin), db: Session = Depends(db_session)
):
    _get_workspace_or_404(db, body.workspace_id)
    if "ingest" in body.scopes and body.source_id is None:
        raise Stack360Error(ErrorCode.VALIDATION_ERROR, "scope 'ingest' exige source_id (key source-bound)")
    ds = None
    if body.source_id is not None:
        ds = db.get(DataSource, body.source_id)
        if ds is None or ds.workspace_id != body.workspace_id:
            raise Stack360Error(ErrorCode.NOT_FOUND, "source não encontrada nesse workspace")

    plaintext, prefix, khash = generate_api_key()
    k = ApiKey(
        workspace_id=body.workspace_id,
        data_source_id=(ds.id if ds else None),
        name=body.name,
        key_prefix=prefix,
        key_hash=khash,
        scopes=body.scopes,
    )
    db.add(k)
    db.commit()
    return {
        "id": str(k.id),
        "name": k.name,
        "key_prefix": k.key_prefix,
        "scopes": k.scopes,
        "plaintext": plaintext,
    }


@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: uuid.UUID, ctx: AuthContext = Depends(require_admin), db: Session = Depends(db_session)):
    k = db.get(ApiKey, key_id)
    if k is None:
        raise Stack360Error(ErrorCode.NOT_FOUND, "api key não encontrada")
    k.status = "revoked"
    k.revoked_at = utcnow()
    db.commit()
    return {"id": str(k.id), "status": k.status}
