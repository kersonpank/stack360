from __future__ import annotations

import pytest

from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def two_ws(client, make_workspace, make_source, make_api_key):
    wa = make_workspace(slug="wa")
    wb = make_workspace(slug="wb")
    sa = make_source(wa, key="sa")
    sb = make_source(wb, key="sb")
    ka, _ = make_api_key(wa, sa, scopes=("ingest", "read"))
    kb, _ = make_api_key(wb, sb, scopes=("ingest", "read"))
    return Caller(client, ka), Caller(client, kb)


def test_context_shape_and_unification(two_ws):
    a, _ = two_ws
    r = a.ingest(ev("identity.observed", identities=email("u@x.com"), company={"cnpj": "99999999000199", "name": "X"}))
    pid = r.json()["entities"]["person_id"]
    a.ingest(ev("interaction.email_opened", identities=email("u@x.com"), context={"channel": "email", "direction": "inbound"}))
    a.ingest(ev("observation.recorded", identities=email("u@x.com"), data={"key": "role", "value": "buyer"}))
    a.ingest(ev("score.calculated", identities=email("u@x.com"),
               data={"score_key": "fit", "score_value": 72, "score_band": "high", "engine_name": "e", "engine_version": "1"}))

    ctx = a.get(f"/api/v1/people/{pid}/context").json()
    assert set(ctx.keys()) == {
        "person", "identities", "companies", "recent_interactions",
        "observations", "experience_runs", "results", "scores",
    }
    assert ctx["identities"][0]["identity_type"] == "email"
    assert len(ctx["recent_interactions"]) == 1
    assert ctx["observations"][0]["key"] == "role"
    assert ctx["scores"][0]["score_key"] == "fit" and ctx["scores"][0]["score_value"] == 72.0
    assert len(ctx["companies"]) == 1


def test_context_include_and_limit(two_ws):
    a, _ = two_ws
    r = a.ingest(ev("identity.observed", identities=email("lim@x.com")))
    pid = r.json()["entities"]["person_id"]
    ctx = a.get(f"/api/v1/people/{pid}/context", include="identities").json()
    assert "identities" in ctx and "recent_interactions" not in ctx


# workspace isolation — A não lê Person de B
def test_workspace_isolation(two_ws):
    a, b = two_ws
    r = b.ingest(ev("identity.observed", identities=email("secret@b.com")))
    pid_b = r.json()["entities"]["person_id"]
    assert a.get(f"/api/v1/people/{pid_b}").status_code == 404
    assert a.get(f"/api/v1/people/{pid_b}/context").status_code == 404
    # e A não encontra por identidade
    assert a.get("/api/v1/people", identity_type="email", identity_value="secret@b.com").json()["items"] == []


def test_find_person_by_identity(two_ws):
    a, _ = two_ws
    a.ingest(ev("identity.observed", identities=email("find@x.com")))
    items = a.get("/api/v1/people", identity_type="email", identity_value="FIND@x.com").json()["items"]
    assert len(items) == 1
