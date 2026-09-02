"""Bootstrap da migration canônica em DB local vazio — via `alembic stamp` +
`upgrade` (NUNCA `upgrade head`, que não sobe em DB vazio). Valida 21 tabelas,
downgrade e re-apply. `public` fica intocado."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.stack360.conftest import TEST_URL

MIG_DB = "stack360_migtest"
_admin_url = TEST_URL.rsplit("/", 1)[0] + "/postgres"
_mig_url = TEST_URL.rsplit("/", 1)[0] + f"/{MIG_DB}"


def _alembic(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["NORMALIZER_DATABASE_URL"] = _mig_url
    env["DATABASE_URL"] = _mig_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd(),
    )


@pytest.fixture()
def fresh_db():
    adm = create_engine(_admin_url, isolation_level="AUTOCOMMIT")
    with adm.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {MIG_DB} WITH (FORCE)"))
        c.execute(text(f"CREATE DATABASE {MIG_DB} OWNER stack360"))
    yield _mig_url
    with adm.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {MIG_DB} WITH (FORCE)"))
    adm.dispose()


def test_stamp_then_upgrade_then_downgrade(fresh_db):
    r = _alembic("stamp", "13b31f818410")
    assert r.returncode == 0, r.stderr

    r = _alembic("upgrade", "aa47386e4e9f")
    assert r.returncode == 0, r.stderr

    eng = create_engine(fresh_db)
    insp = inspect(eng)
    tables = sorted(insp.get_table_names(schema="stack360"))
    assert len(tables) == 21, tables
    # public só tem alembic_version — nenhuma tabela legada foi criada
    assert insp.get_table_names(schema="public") == ["alembic_version"]

    r = _alembic("downgrade", "13b31f818410")
    assert r.returncode == 0, r.stderr
    insp = inspect(create_engine(fresh_db))
    assert "stack360" not in insp.get_schema_names()

    r = _alembic("upgrade", "aa47386e4e9f")
    assert r.returncode == 0, r.stderr
    insp = inspect(create_engine(fresh_db))
    assert len(insp.get_table_names(schema="stack360")) == 21


def test_migration_ddl_has_no_create_extension():
    # a DDL executável (STACK360_DDL) não pode exigir pgcrypto/extensão
    import importlib.util
    from pathlib import Path

    path = Path("alembic/versions/aa47386e4e9f_stack360_core.py")
    spec = importlib.util.spec_from_file_location("_mig", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "CREATE EXTENSION" not in mod.STACK360_DDL.upper()
    assert "GEN_RANDOM_UUID" not in mod.STACK360_DDL.upper()
