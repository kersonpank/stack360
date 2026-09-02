from __future__ import annotations

import base64
import json
import time
from typing import Optional

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.stack360.auth import AuthContext, require_scope, resolve_api_key, resolve_source
from app.stack360.config import get_settings
from app.stack360.db import get_db, get_sessionmaker
from app.stack360.schemas.errors import ErrorCode, Stack360Error

# rate limit best-effort em memória, por api_key.id (NÃO distribuído)
_buckets: dict[str, list[float]] = {}


def _rate_limit(ctx: AuthContext) -> None:
    limit = get_settings().rate_limit_per_min
    if limit <= 0:
        return
    now = time.monotonic()
    key = str(ctx.api_key_id)
    window = _buckets.setdefault(key, [])
    cutoff = now - 60.0
    window[:] = [t for t in window if t > cutoff]
    if len(window) >= limit:
        raise Stack360Error(ErrorCode.RATE_LIMITED, "limite de requisições excedido")
    window.append(now)


def db_session() -> Session:  # pragma: no cover - wrapper
    yield from get_db()


def _auth(
    db: Session,
    authorization: Optional[str],
    x_api_key: Optional[str],
    scope: str,
) -> AuthContext:
    ctx = resolve_api_key(db, x_api_key or _bearer(authorization))
    require_scope(ctx, scope)
    _rate_limit(ctx)
    db.commit()  # persiste last_used_at
    return ctx


def _bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def require_ingest(
    db: Session = Depends(db_session),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    ctx = _auth(db, authorization, x_api_key, "ingest")
    resolve_source(db, ctx)  # 403 SOURCE_DISABLED se a data_source não estiver ativa
    return ctx


def require_read(
    db: Session = Depends(db_session),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    return _auth(db, authorization, x_api_key, "read")


def sessionmaker_dep():
    return get_sessionmaker()


# ----------------------------------------------------------------------
# Paginação por cursor (opaco)
# ----------------------------------------------------------------------
def encode_cursor(sort_value, id_value) -> str:
    raw = json.dumps([str(sort_value), str(id_value)]).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: Optional[str]):
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        s, i = json.loads(raw)
        return s, i
    except Exception as exc:  # noqa: BLE001
        raise Stack360Error(ErrorCode.VALIDATION_ERROR, "cursor inválido") from exc


class PageParams:
    def __init__(
        self,
        limit: int = Query(default=None),
        cursor: Optional[str] = Query(default=None),
    ):
        s = get_settings()
        self.limit = min(limit or s.read_page_default, s.read_page_max)
        self.cursor = decode_cursor(cursor)
