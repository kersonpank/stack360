import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

_writer_engine: Engine | None = None


def get_writer_engine() -> Engine:
    global _writer_engine
    if _writer_engine is None:
        if not settings.normalizer_database_url:
            print(
                "ERRO: NORMALIZER_DATABASE_URL nao esta configurada. "
                "Defina-a no .env antes de rodar o worker em modo real.",
                file=sys.stderr,
            )
            sys.exit(1)
        _writer_engine = create_engine(
            settings.normalizer_database_url,
            poolclass=NullPool,
            connect_args={"options": "-c lock_timeout=30000 -c statement_timeout=120000"},
        )
    return _writer_engine


def get_writer_session() -> Session:
    SessionLocal = sessionmaker(bind=get_writer_engine(), autocommit=False, autoflush=False)
    return SessionLocal()
