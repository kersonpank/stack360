from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.stack360.models.ingestion_event import IngestionEvent
from app.stack360.models.observation import Observation
from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def cc(client, make_workspace, make_source, make_api_key, make_experience):
    w = make_workspace()
    s = make_source(w, key="src-x")
    k, _ = make_api_key(w, s, scopes=("ingest", "read"))
    make_experience(w, key="diag", version="1")
    return w, s, Caller(client, k)


# L / idempotência — mesmo event_id => zero duplicação
def test_idempotency_same_event_id(cc, db):
    _, _, c = cc
    e = ev("observation.recorded", identities=email("i@x.com"),
           data={"key": "freq", "value": "weekly"}, event_id="dup-1")
    r1 = c.ingest(e)
    r2 = c.ingest(e)
    assert r1.json()["status"] == "accepted"
    assert r2.json()["status"] == "duplicate" and r2.json()["duplicate"] is True
    assert db.execute(select(func.count()).select_from(Observation)).scalar_one() == 1
    assert db.execute(select(func.count()).select_from(IngestionEvent)).scalar_one() == 1


# K — mesmo valor em DOIS eventos diferentes => 2 observations (evidência temporal)
def test_observation_temporal_repetition(cc, db):
    _, _, c = cc
    c.ingest(ev("observation.recorded", identities=email("t@x.com"),
               data={"key": "ma_freq", "value": "weekly"}, event_id="jan",
               occurred_at="2026-01-15T00:00:00Z"))
    c.ingest(ev("observation.recorded", identities=email("t@x.com"),
               data={"key": "ma_freq", "value": "weekly"}, event_id="aug",
               occurred_at="2026-08-15T00:00:00Z"))
    assert db.execute(select(func.count()).select_from(Observation)).scalar_one() == 2


# A — raw sobrevive a falha do handler
def test_raw_survives_handler_failure(cc, db):
    _, _, c = cc
    r = c.ingest(ev("experience.run_started",
                    context={"experience_key": "ghost", "experience_version": "9", "external_run_id": "R"},
                    event_id="fail-1"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "EXPERIENCE_NOT_FOUND"
    ie = db.execute(select(IngestionEvent).where(IngestionEvent.external_event_id == "fail-1")).scalar_one()
    assert ie.status == "failed" and ie.error_code == "EXPERIENCE_NOT_FOUND" and ie.retry_count == 1


def test_batch_per_item_status(cc, db):
    _, _, c = cc
    good = ev("identity.observed", identities=email("g@x.com"), event_id="b-good")
    dup = dict(good)  # mesmo event_id -> duplicate no 2º
    bad = ev("experience.run_started",
             context={"experience_key": "ghost", "experience_version": "1", "external_run_id": "R"},
             event_id="b-bad")
    r = c.batch([good, dup, bad])
    assert r.status_code == 200
    statuses = [it["status"] for it in r.json()["results"]]
    assert statuses == ["accepted", "duplicate", "error"]
    assert r.json()["results"][2]["error"]["code"] == "EXPERIENCE_NOT_FOUND"


def test_batch_limit(cc):
    _, _, c = cc
    from app.stack360.config import get_settings

    n = get_settings().batch_max + 1
    events = [ev("identity.observed", identities=email(f"{i}@x.com")) for i in range(n)]
    r = c.batch(events)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_schema_unsupported(cc):
    _, _, c = cc
    e = ev("identity.observed", identities=email("s@x.com"))
    e["schema_version"] = "2.0"
    r = c.ingest(e)
    assert r.status_code == 400 and r.json()["error"]["code"] == "SCHEMA_UNSUPPORTED"


def test_error_contract_shape(cc):
    _, _, c = cc
    r = c.ingest({"schema_version": "1.0"})  # inválido
    assert r.status_code == 422
    body = r.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message", "details"}
    assert "Traceback" not in body["error"]["message"]


# ─────────────────────────── H2 — EVENT_ID_CONFLICT ───────────────────────────
def test_same_event_id_same_payload_is_duplicate(cc):
    _, _, c = cc
    e = ev("identity.observed", identities=email("h2@x.com"), event_id="h2-a")
    assert c.ingest(e).json()["status"] == "accepted"
    assert c.ingest(dict(e)).json()["status"] == "duplicate"


def test_same_event_id_different_payload_conflicts(cc, db):
    from sqlalchemy import func, select

    from app.stack360.models.resolution import ResolutionCase

    _, _, c = cc
    e1 = ev("identity.observed", identities=email("h2-orig@x.com"), event_id="h2-b")
    r1 = c.ingest(e1)
    assert r1.status_code == 200

    ie = db.execute(select(IngestionEvent).where(IngestionEvent.external_event_id == "h2-b")).scalar_one()
    orig_hash, orig_payload, orig_status = ie.payload_hash, dict(ie.payload), ie.status

    e2 = ev("identity.observed", identities=email("h2-DIFFERENT@x.com"), event_id="h2-b")
    r2 = c.ingest(e2)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "EVENT_ID_CONFLICT"
    d = r2.json()["error"]["details"]
    assert d["existing_payload_hash"] == orig_hash
    assert d["incoming_payload_hash"] != orig_hash

    db.expire_all()
    ie2 = db.execute(select(IngestionEvent).where(IngestionEvent.external_event_id == "h2-b")).scalar_one()
    assert ie2.payload_hash == orig_hash  # ORIGINAL intacto
    assert dict(ie2.payload) == orig_payload
    assert ie2.status == orig_status
    assert ie2.retry_count == 0

    cases = db.execute(
        select(ResolutionCase).where(ResolutionCase.case_type == "event_id_conflict")
    ).scalars().all()
    assert len(cases) == 1

    # repetir o payload conflitante -> ainda 1 caso
    assert c.ingest(dict(e2)).status_code == 409
    db.expire_all()
    cases = db.execute(
        select(func.count()).select_from(ResolutionCase).where(ResolutionCase.case_type == "event_id_conflict")
    ).scalar_one()
    assert cases == 1


def test_same_event_id_different_event_type_conflicts(cc):
    _, _, c = cc
    c.ingest(ev("identity.observed", identities=email("h2-t@x.com"), event_id="h2-c"))
    r = c.ingest(ev("interaction.message_received", identities=email("h2-t@x.com"),
                    context={"channel": "web"}, event_id="h2-c"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "EVENT_ID_CONFLICT"
