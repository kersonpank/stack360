from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.stack360.mcp import tools as T
from app.stack360.models.person import Person
from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def setup(client, make_workspace, make_source, make_api_key):
    wa = make_workspace(slug="rc-a")
    wb = make_workspace(slug="rc-b")
    sa = make_source(wa)
    sb = make_source(wb)
    ka, ka_row = make_api_key(wa, sa, scopes=("ingest", "read", "mcp"))
    kb, _ = make_api_key(wb, sb, scopes=("ingest", "read", "mcp"))
    return wa, wb, ka_row, Caller(client, ka), Caller(client, kb)


def _make_conflict(c: Caller) -> str:
    c.ingest(ev("identity.observed", identities=email("c1@x.com")))
    c.ingest(ev("identity.observed", identities=[{"type": "phone", "value": "+5511911112222"}]))
    r = c.ingest(ev("identity.observed",
                    identities=email("c1@x.com") + [{"type": "phone", "value": "+5511911112222"}],
                    event_id="cx"))
    return r.json()["error"]["details"]["resolution_case_id"] if r.status_code == 409 else None


def test_rest_list_and_get(setup):
    _, _, _, a, _ = setup
    case_id = _make_conflict(a)
    assert case_id

    lst = a.get("/api/v1/resolution-cases", case_type="identity_conflict").json()["items"]
    assert len(lst) == 1 and lst[0]["id"] == case_id
    detail = a.get(f"/api/v1/resolution-cases/{case_id}").json()
    assert detail["case_type"] == "identity_conflict" and detail["recommendations"] == []


# N — workspace isolation em resolution_cases
def test_workspace_isolation_cases(setup):
    _, _, _, a, b = setup
    case_id = _make_conflict(a)
    assert b.get("/api/v1/resolution-cases").json()["items"] == []
    assert b.get(f"/api/v1/resolution-cases/{case_id}").status_code == 404


# O — agente/MCP cria recommendation mas NÃO faz merge de Person
def test_mcp_recommendation_only(setup, db, Session_):
    wa, _, ka_row, a, _ = setup
    case_id = _make_conflict(a)
    from app.stack360.auth import AuthContext

    auth = AuthContext(
        api_key_id=ka_row.id, workspace_id=wa.id, workspace_slug="rc-a",
        data_source_id=ka_row.data_source_id, data_source_key="x", scopes=frozenset({"read", "mcp"}),
    )
    n_before = db.execute(select(func.count()).select_from(Person)).scalar_one()
    out = T.submit_resolution_recommendation(
        auth, Session_, resolution_case_id=case_id,
        recommended_action="merge_persons", evidence={"reason": "same person"},
        confidence=0.9, summary="parecem a mesma pessoa", agent_name="dq-agent", agent_version="0.1",
    )
    assert "recommendation_id" in out and out["case_status"] == "recommendation_ready"
    # NENHUMA Person foi mesclada/criada
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == n_before
    # a tool NÃO expõe nada capaz de merge
    assert not hasattr(T, "merge_persons")
    detail = a.get(f"/api/v1/resolution-cases/{case_id}").json()
    assert detail["recommendations"][0]["recommended_action"] == "merge_persons"
    assert "chain_of_thought" not in detail["recommendations"][0]
