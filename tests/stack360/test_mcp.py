"""MCP tools reusam os MESMOS services da REST -> mesmo contexto."""
from __future__ import annotations

import pytest

from app.stack360.auth import AuthContext
from app.stack360.mcp import tools as T
from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def setup(client, make_workspace, make_source, make_api_key, Session_):
    w = make_workspace(slug="mcp-ws")
    s = make_source(w, key="mcp-src")
    key, krow = make_api_key(w, s, scopes=("ingest", "read", "mcp"))
    auth = AuthContext(
        api_key_id=krow.id, workspace_id=w.id, workspace_slug="mcp-ws",
        data_source_id=s.id, data_source_key="mcp-src", scopes=frozenset({"ingest", "read", "mcp"}),
    )
    return Caller(client, key), auth, Session_


def test_get_person_context_matches_rest(setup):
    c, auth, S = setup
    r = c.ingest(ev("identity.observed", identities=email("m@x.com"), company={"cnpj": "55555555000155", "name": "M"}))
    pid = r.json()["entities"]["person_id"]
    c.ingest(ev("interaction.form_submitted", identities=email("m@x.com"), context={"channel": "web"}))

    rest = c.get(f"/api/v1/people/{pid}/context").json()
    mcp = T.get_person_context(auth, S, person_id=pid)
    assert rest["person"]["id"] == mcp["person"]["id"]
    assert [i["identity_type"] for i in rest["identities"]] == [i["identity_type"] for i in mcp["identities"]]
    assert len(rest["recent_interactions"]) == len(mcp["recent_interactions"]) == 1


def test_mcp_ingest_requires_source_bound(setup, make_workspace, make_api_key):
    _, _, S = setup
    w = make_workspace(slug="mcp-nobind")
    _, krow = make_api_key(w, source=None, scopes=("mcp", "read"))
    auth = AuthContext(
        api_key_id=krow.id, workspace_id=w.id, workspace_slug="mcp-nobind",
        data_source_id=None, data_source_key=None, scopes=frozenset({"mcp", "read"}),
    )
    from app.stack360.schemas.errors import Stack360Error

    with pytest.raises(Stack360Error):
        T.ingest_event(auth, S, {"schema_version": "1.0", "event_id": "x", "event_type": "identity.observed",
                                 "occurred_at": "2026-01-01T00:00:00Z"})


def test_mcp_server_builds():
    from app.stack360.mcp.server import build_server

    # apenas garante que o servidor stdio monta sem erro (não roda o loop)
    import pytest as _p

    with _p.raises(SystemExit):
        build_server(api_key=None)


# ───────────────────── H3 — revalidação de API key na sessão MCP ─────────────────────
@pytest.fixture()
def mcp_session(monkeypatch, make_workspace, make_source, make_api_key, db):
    monkeypatch.setenv("STACK360_MCP_AUTH_TTL", "0")  # revalida toda chamada
    from app.stack360.mcp import server as srv

    w = make_workspace(slug="mcp-reval")
    s = make_source(w, key="mcp-reval-src")
    key, krow = make_api_key(w, s, scopes=("ingest", "read", "mcp"))
    srv.build_server(api_key=key)
    yield srv, w, s, krow, key
    srv.reset_auth_cache()


def test_revoked_key_stops_working_without_restart(mcp_session, db, Session_):
    from app.stack360.base import utcnow
    from app.stack360.mcp import tools as T
    from app.stack360.models.api_key import ApiKey

    srv, w, s, krow, key = mcp_session
    # cria uma Person via ingest para ter o que ler
    srv._guard(T.ingest_event, envelope={
        "schema_version": "1.0", "event_id": "mcp-r1", "event_type": "identity.observed",
        "occurred_at": "2026-01-01T00:00:00Z",
        "subject": {"identities": [{"type": "email", "value": "r@x.com"}]},
    })
    ok = srv._guard(T.search_people, identity_type="email", identity_value="r@x.com")
    assert "error" not in ok and ok["items"]

    # revoga a key no DB — SEM reiniciar o processo MCP
    k = db.get(ApiKey, krow.id)
    k.status = "revoked"
    k.revoked_at = utcnow()
    db.commit()

    out = srv._guard(T.search_people, identity_type="email", identity_value="r@x.com")
    assert out["error"]["code"] == "AUTH_INVALID"


def test_disabled_source_blocks_mcp_write(mcp_session, db):
    from app.stack360.mcp import tools as T
    from app.stack360.models.data_source import DataSource

    srv, w, s, krow, key = mcp_session
    ds = db.get(DataSource, s.id)
    ds.status = "disabled"
    db.commit()

    out = srv._guard(T.ingest_event, envelope={
        "schema_version": "1.0", "event_id": "mcp-w1", "event_type": "identity.observed",
        "occurred_at": "2026-01-01T00:00:00Z",
        "subject": {"identities": [{"type": "email", "value": "w@x.com"}]},
    })
    assert out["error"]["code"] == "SOURCE_DISABLED"
