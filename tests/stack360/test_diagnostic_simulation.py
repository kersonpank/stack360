"""Simula os eventos do Diagnóstico de Expansão MA (SEM tocar no diagnóstico real).

    anonymous visitor -> answers -> email/company -> Person -> Company -> Result -> context API
"""
from __future__ import annotations

import pytest

from tests.stack360._helpers import Caller, ev


@pytest.fixture()
def diag(client, make_workspace, make_source, make_api_key, make_experience):
    w = make_workspace(slug="stack360-empresas")
    s = make_source(w, key="diagnostico-expansao-ma", source_type="diagnostic")
    k, _ = make_api_key(w, s, scopes=("ingest", "read"))
    make_experience(w, key="diagnostico-expansao-ma", version="1", exp_type="diagnostic")
    return Caller(client, k)


def _ctx(**kw):
    base = {"experience_key": "diagnostico-expansao-ma", "experience_version": "1", "external_run_id": "RUN-42", "visitor_id": "visit-9"}
    base.update(kw)
    return base


def test_full_diagnostic_flow(diag, db):
    c = diag

    r = c.ingest(ev("experience.run_started", context=_ctx(),
                    attribution={"utm_source": "meta", "utm_campaign": "ma-2026"}))
    run_id = r.json()["entities"]["run_id"]
    assert r.status_code == 200

    # visitor anônimo: run sem person_id
    run = c.get(f"/api/v1/runs/{run_id}").json()["run"]
    assert run["person_id"] is None and run["visitor_id"] == "visit-9"
    assert run["utm"]["campaign"] == "ma-2026"

    for i, (q, v) in enumerate([("ma_recipients", "21_50"), ("current_modal", "rodoviario"), ("urgency", "alta")]):
        c.ingest(ev("experience.answer_recorded", context=_ctx(),
                    data={"question_key": q, "value": v}, event_id=f"ans-{i}"))

    # identity_captured: email + company
    c.ingest(ev("experience.identity_captured", context=_ctx(),
                identities=[{"type": "email", "value": "joao@empresaabc.com.br"}],
                company={"cnpj": "12.345.678/0001-99", "name": "Empresa ABC Ltda", "domain": "empresaabc.com.br"},
                event_id="idcap"))

    run = c.get(f"/api/v1/runs/{run_id}").json()["run"]
    assert run["person_id"] is not None and run["company_id"] is not None
    pid = run["person_id"]

    # run_completed + result
    c.ingest(ev("experience.run_completed", context=_ctx(),
                data={"result": {"tier": "A", "dimensions": {"fit": 0.8}}, "score": 87, "verdict": "go",
                      "score_band": "alto", "engine_name": "ma-engine", "engine_version": "1.2"},
                event_id="done"))

    detail = c.get(f"/api/v1/runs/{run_id}").json()
    assert detail["run"]["status"] == "completed"
    assert detail["answers_count"] == 3
    assert {a["question_key"] for a in detail["answers_latest"]} == {"ma_recipients", "current_modal", "urgency"}
    assert detail["results"][0]["score"] == 87.0 and detail["results"][0]["verdict"] == "go"

    # context API tem o run + result
    ctx = c.get(f"/api/v1/people/{pid}/context").json()
    assert any(rn["experience_key"] == "diagnostico-expansao-ma" for rn in ctx["experience_runs"])
    assert ctx["results"] and ctx["results"][0]["score"] == 87.0
    assert ctx["companies"] and ctx["companies"][0]["company"]["cnpj_normalized"] == "12345678000199"
