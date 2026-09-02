"""Engine/session do Stack360. Nunca aponta para o banco legado de produção
nesta task — usa ``STACK360_DATABASE_URL`` (local)."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.stack360 import SCHEMA
from app.stack360.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _resolve_url() -> str:
    # Prioridade: env explícita de teste > config
    return os.environ.get("STACK360_DATABASE_URL_OVERRIDE") or get_settings().database_url


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(_resolve_url(), pool_pre_ping=True, future=True)

        @event.listens_for(_engine, "connect")
        def _set_search_path(dbapi_conn, _rec):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.close()

        _SessionLocal = sessionmaker(
            bind=_engine, autocommit=False, autoflush=False, future=True
        )
    return _engine


def get_sessionmaker() -> sessionmaker:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def reset_engine() -> None:
    """Usado por testes para trocar de banco."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def session_scope() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    """Dependency FastAPI — não commita sozinha (rotas de escrita commitam)."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def ping() -> bool:
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
