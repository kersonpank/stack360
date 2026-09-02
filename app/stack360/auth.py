"""Autenticação por API key. Workspace vem SEMPRE da key.

Lookup por ``key_hash`` (UNIQUE) — NÃO depende de unicidade de ``key_prefix``.
Scope ``ingest`` exige key source-bound (``data_source_id`` NOT NULL).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.base import utcnow
from app.stack360.models.api_key import ApiKey
from app.stack360.models.data_source import DataSource
from app.stack360.models.workspace import Workspace
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.security.hashing import sha256_hex

VALID_SCOPES = {"ingest", "read", "mcp"}


@dataclass(frozen=True)
class AuthContext:
    api_key_id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_slug: str
    data_source_id: Optional[uuid.UUID]
    data_source_key: Optional[str]
    scopes: frozenset[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


def _extract_key(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    if x_api_key:
        return x_api_key.strip()
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()
    return None


def resolve_api_key(db: Session, presented_key: Optional[str]) -> AuthContext:
    if not presented_key:
        raise Stack360Error(ErrorCode.AUTH_INVALID, "API key ausente")

    key_hash = sha256_hex(presented_key)
    row = db.execute(
        select(ApiKey, Workspace.slug, DataSource.key)
        .join(Workspace, Workspace.id == ApiKey.workspace_id)
        .join(DataSource, DataSource.id == ApiKey.data_source_id, isouter=True)
        .where(ApiKey.key_hash == key_hash)
    ).first()
    if row is None:
        raise Stack360Error(ErrorCode.AUTH_INVALID, "API key inválida")

    api_key, ws_slug, ds_key = row
    if api_key.status != "active" or api_key.revoked_at is not None:
        raise Stack360Error(ErrorCode.AUTH_INVALID, "API key revogada ou inativa")

    scopes = frozenset(api_key.scopes or [])
    if "ingest" in scopes and api_key.data_source_id is None:
        # invariante de segurança: ingest key TEM que ser source-bound
        raise Stack360Error(
            ErrorCode.SCOPE_DENIED,
            "API key com scope 'ingest' precisa estar vinculada a uma data_source",
        )

    api_key.last_used_at = utcnow()  # best-effort; commit fica a cargo da rota

    return AuthContext(
        api_key_id=api_key.id,
        workspace_id=api_key.workspace_id,
        workspace_slug=ws_slug,
        data_source_id=api_key.data_source_id,
        data_source_key=ds_key,
        scopes=scopes,
    )


def require_scope(ctx: AuthContext, scope: str) -> None:
    if not ctx.has_scope(scope):
        raise Stack360Error(
            ErrorCode.SCOPE_DENIED, f"scope '{scope}' necessário", {"have": sorted(ctx.scopes)}
        )


def resolve_source(db: Session, ctx: AuthContext) -> DataSource:
    """Retorna a data_source da key (ingest) e valida que está ativa."""
    if ctx.data_source_id is None:
        raise Stack360Error(ErrorCode.SCOPE_DENIED, "operação exige API key source-bound")
    ds = db.get(DataSource, ctx.data_source_id)
    if ds is None:
        raise Stack360Error(ErrorCode.AUTH_INVALID, "data_source da key não existe")
    if ds.status != "active":
        raise Stack360Error(ErrorCode.SOURCE_DISABLED, f"data_source '{ds.key}' desativada")
    return ds
