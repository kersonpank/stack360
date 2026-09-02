from __future__ import annotations

import pytest

from app.stack360.auth import resolve_api_key
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.security.hashing import sha256_hex


def _ingest(client, key, event):
    return client.post("/api/v1/ingest/events", json=event, headers={"Authorization": f"Bearer {key}"})


EV = {
    "schema_version": "1.0",
    "event_id": "a1",
    "event_type": "identity.observed",
    "occurred_at": "2026-01-01T00:00:00Z",
    "subject": {"identities": [{"type": "email", "value": "x@y.com"}]},
}


def test_valid_key_ingests(client, make_workspace, make_source, make_api_key):
    w = make_workspace()
    s = make_source(w)
    key, _ = make_api_key(w, s, scopes=("ingest",))
    assert _ingest(client, key, EV).status_code == 200


def test_invalid_key(client):
    r = _ingest(client, "st_bogus", EV)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_INVALID"


def test_revoked_key(client, db, make_workspace, make_source, make_api_key):
    from app.stack360.base import utcnow

    w = make_workspace()
    s = make_source(w)
    key, k = make_api_key(w, s, scopes=("ingest",))
    k.status = "revoked"
    k.revoked_at = utcnow()
    db.commit()
    assert _ingest(client, key, EV).status_code == 401


def test_scope_denied(client, make_workspace, make_source, make_api_key):
    w = make_workspace()
    s = make_source(w)
    key, _ = make_api_key(w, s, scopes=("read",))
    r = _ingest(client, key, EV)
    assert r.status_code == 403 and r.json()["error"]["code"] == "SCOPE_DENIED"


def test_source_disabled(client, db, make_workspace, make_source, make_api_key):
    w = make_workspace()
    s = make_source(w, status="disabled")
    key, _ = make_api_key(w, s, scopes=("ingest",))
    r = _ingest(client, key, EV)
    assert r.status_code == 403 and r.json()["error"]["code"] == "SOURCE_DISABLED"


# M — ingest key SEM data_source é rejeitada
def test_ingest_key_must_be_source_bound(client, db, make_workspace, make_api_key):
    w = make_workspace()
    key, _ = make_api_key(w, source=None, scopes=("ingest",))
    r = _ingest(client, key, EV)
    assert r.status_code == 403 and r.json()["error"]["code"] == "SCOPE_DENIED"


def test_admin_rejects_ingest_key_without_source(db, make_workspace):
    import argparse

    from app.stack360.admin import cmd_create_api_key

    w = make_workspace(slug="adm-ws")
    ns = argparse.Namespace(workspace="adm-ws", source=None, name="k", scopes="ingest,read")
    with pytest.raises(SystemExit):
        cmd_create_api_key(ns)


# apikey lookup — NÃO depende de unicidade de key_prefix
def test_lookup_by_hash_not_prefix(db, Session_, make_workspace, make_source, make_api_key):
    w = make_workspace()
    s = make_source(w)
    # duas keys forçadas ao MESMO key_prefix — o lookup deve resolver pelo hash
    k1_plain, k1 = make_api_key(w, s, scopes=("ingest",), prefix_override="st_SAMEPREFIX")
    k2_plain, k2 = make_api_key(w, s, scopes=("read",), prefix_override="st_SAMEPREFIX")
    assert k1.key_prefix == k2.key_prefix
    assert k1.key_hash != k2.key_hash

    with Session_() as sdb:
        c1 = resolve_api_key(sdb, k1_plain)
        c2 = resolve_api_key(sdb, k2_plain)
    assert c1.api_key_id == k1.id and "ingest" in c1.scopes
    assert c2.api_key_id == k2.id and "read" in c2.scopes and "ingest" not in c2.scopes
