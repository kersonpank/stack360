from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from app.stack360.models.ingestion_event import IngestionEvent
from app.stack360.models.webhook import WebhookEndpoint


@pytest.fixture()
def wh(client, db, make_workspace, make_source, make_api_key):
    w = make_workspace(slug="wh-ws")
    s_a = make_source(w, key="wh-src-a", source_type="custom")
    s_b = make_source(w, key="wh-src-b", source_type="custom")
    key_a, _ = make_api_key(w, s_a, scopes=("ingest",))
    key_b, _ = make_api_key(w, s_b, scopes=("ingest",))
    ep = WebhookEndpoint(
        workspace_id=w.id, data_source_id=s_a.id, source_key="hook-a",
        mapping={"event_type": "interaction.webhook", "event_id_path": "id"},
    )
    db.add(ep)
    db.commit()
    return client, key_a, key_b


def test_inbound_passthrough_with_api_key(wh, db):
    client, key_a, _ = wh
    body = {"id": "evt-1", "text": "hello"}
    r = client.post("/api/v1/webhooks/hook-a", content=json.dumps(body),
                    headers={"Authorization": f"Bearer {key_a}", "content-type": "application/json"})
    assert r.status_code == 200 and r.json()["accepted"] is True
    ie = db.execute(select(IngestionEvent).where(IngestionEvent.external_event_id == "evt-1")).scalar_one()
    assert ie.event_type == "interaction.webhook"
    assert ie.payload["data"]["text"] == "hello"


# P — key da Source B NÃO pode publicar no endpoint da Source A
def test_cross_source_key_rejected(wh):
    client, _, key_b = wh
    r = client.post("/api/v1/webhooks/hook-a", content=json.dumps({"id": "x"}),
                    headers={"Authorization": f"Bearer {key_b}", "content-type": "application/json"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "SCOPE_DENIED"


def test_unknown_source_key(wh):
    client, key_a, _ = wh
    r = client.post("/api/v1/webhooks/nope", content=b"{}",
                    headers={"Authorization": f"Bearer {key_a}"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "SOURCE_DISABLED"


def test_disabled_endpoint(wh, db):
    client, key_a, _ = wh
    ep = db.execute(select(WebhookEndpoint).where(WebhookEndpoint.source_key == "hook-a")).scalar_one()
    ep.status = "disabled"
    db.commit()
    r = client.post("/api/v1/webhooks/hook-a", content=b"{}", headers={"Authorization": f"Bearer {key_a}"})
    assert r.status_code == 403
