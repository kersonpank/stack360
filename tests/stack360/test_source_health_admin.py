from __future__ import annotations

import argparse
import json

import pytest
from sqlalchemy import select

from app.stack360.models.experience import Experience
from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def cc(client, make_workspace, make_source, make_api_key):
    w = make_workspace(slug="sh-ws")
    s = make_source(w, key="sh-src")
    k, _ = make_api_key(w, s, scopes=("ingest", "read"))
    return w, s, Caller(client, k)


def test_source_health_reflects_events(cc):
    _, _, c = cc
    c.ingest(ev("identity.observed", identities=email("h@x.com")))
    c.ingest(ev("experience.run_started",
                context={"experience_key": "ghost", "experience_version": "1", "external_run_id": "R"},
                event_id="bad"))  # falha
    health = c.get("/api/v1/sources/health").json()["items"]
    row = next(r for r in health if r["source_key"] == "sh-src")
    assert row["events_24h"] == 2
    assert row["failed_24h"] == 1
    assert row["last_success_at"] is not None
    assert row["last_error_at"] is not None
    assert row["feeding"] is True


def test_list_sources(cc):
    _, _, c = cc
    items = c.get("/api/v1/sources").json()["items"]
    assert any(i["key"] == "sh-src" for i in items)


# ---- Admin CLI ----
def test_cli_create_experience_idempotent(db, make_workspace, capsys):
    from app.stack360.admin import cmd_create_experience

    make_workspace(slug="cli-ws")
    ns = argparse.Namespace(workspace="cli-ws", key="diag", version="1", name="D", type="diagnostic")
    cmd_create_experience(ns)
    out1 = json.loads(capsys.readouterr().out.strip())
    cmd_create_experience(argparse.Namespace(workspace="cli-ws", key="diag", version="1", name="D2", type="quiz"))
    out2 = json.loads(capsys.readouterr().out.strip())
    assert out2.get("upserted") is True
    rows = db.execute(select(Experience).where(Experience.key == "diag")).scalars().all()
    assert len(rows) == 1 and rows[0].name == "D2"


def test_cli_create_webhook_endpoint(db, make_workspace, make_source, capsys):
    from app.stack360.admin import cmd_create_webhook_endpoint
    from app.stack360.models.webhook import WebhookEndpoint

    w = make_workspace(slug="cli-wh")
    s = make_source(w, key="cli-wh-src")
    cmd_create_webhook_endpoint(
        argparse.Namespace(workspace="cli-wh", source="cli-wh-src", source_key="cli-hook",
                           signature_header=None, signature_scheme=None)
    )
    capsys.readouterr()
    ep = db.execute(select(WebhookEndpoint).where(WebhookEndpoint.source_key == "cli-hook")).scalar_one()
    assert ep.data_source_id == s.id and ep.workspace_id == w.id
    # secret nunca em plaintext no banco
    assert ep.secret_encrypted is None or isinstance(ep.secret_encrypted, (bytes, memoryview))
