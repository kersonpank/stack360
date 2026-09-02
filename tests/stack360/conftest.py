"""Fixtures do Stack360. Exigem Postgres REAL (local). Se indisponível, SKIP —
a suíte legada offline continua intacta.

    docker compose -f docker-compose.stack360.yml up -d
"""
from __future__ import annotations

import os
import uuid

import pytest

TEST_URL = os.environ.get(
    "STACK360_TEST_DATABASE_URL",
    "postgresql+psycopg2://stack360:stack360@localhost:5433/stack360_test",
)
os.environ["STACK360_DATABASE_URL_OVERRIDE"] = TEST_URL

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402


def pytest_configure(config):  # noqa: D401
    config.addinivalue_line("markers", "pg: exige Postgres real do Stack360 (docker-compose)")


def _pg_available() -> bool:
    try:
        eng = create_engine(TEST_URL)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.pg

if not _pg_available():  # pragma: no cover
    pytest.skip(
        "Postgres do Stack360 indisponível (docker compose -f docker-compose.stack360.yml up -d)",
        allow_module_level=True,
    )

from app.stack360 import db as s360db  # noqa: E402
from app.stack360.base import Stack360Base  # noqa: E402
import app.stack360.models  # noqa: E402,F401
from app.stack360.models import ALL_MODELS  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    s360db.reset_engine()
    eng = s360db.get_engine()
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS stack360 CASCADE"))
        c.execute(text("CREATE SCHEMA stack360"))
    Stack360Base.metadata.create_all(eng)
    yield
    s360db.reset_engine()


@pytest.fixture(autouse=True)
def _truncate():
    yield
    eng = s360db.get_engine()
    names = ", ".join(f"stack360.{m.__tablename__}" for m in ALL_MODELS)
    with eng.begin() as c:
        c.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def Session_():
    return s360db.get_sessionmaker()


@pytest.fixture
def db(Session_):
    s = Session_()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


# ----------------------------------------------------------------------
# Factories
# ----------------------------------------------------------------------
@pytest.fixture
def make_workspace(db):
    from app.stack360.models.workspace import Workspace

    def _make(slug: str | None = None, name: str = "WS"):
        w = Workspace(slug=slug or f"ws-{uuid.uuid4().hex[:8]}", name=name)
        db.add(w)
        db.commit()
        db.refresh(w)
        return w

    return _make


@pytest.fixture
def make_source(db):
    from app.stack360.models.data_source import DataSource

    def _make(workspace, key: str | None = None, source_type: str = "custom", status: str = "active"):
        ds = DataSource(
            workspace_id=workspace.id,
            key=key or f"src-{uuid.uuid4().hex[:8]}",
            name="Source",
            source_type=source_type,
            status=status,
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)
        return ds

    return _make


@pytest.fixture
def make_api_key(db):
    from app.stack360.models.api_key import ApiKey
    from app.stack360.security.hashing import generate_api_key

    def _make(workspace, source=None, scopes=("ingest",), prefix_override: str | None = None):
        plaintext, prefix, khash = generate_api_key()
        k = ApiKey(
            workspace_id=workspace.id,
            data_source_id=(source.id if source else None),
            name="key",
            key_prefix=prefix_override or prefix,
            key_hash=khash,
            scopes=list(scopes),
        )
        db.add(k)
        db.commit()
        db.refresh(k)
        return plaintext, k

    return _make


@pytest.fixture
def make_experience(db):
    from app.stack360.models.experience import Experience

    def _make(workspace, key="diag", version="1", exp_type="diagnostic"):
        e = Experience(
            workspace_id=workspace.id, key=key, version=version, name="Exp", experience_type=exp_type
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    return _make


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.stack360.main import app

    with TestClient(app) as c:
        yield c
