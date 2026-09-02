from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.stack360.models.company import Company
from app.stack360.models.resolution import ResolutionCase
from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def cc(client, make_workspace, make_source, make_api_key):
    w = make_workspace()
    s = make_source(w)
    k, _ = make_api_key(w, s, scopes=("ingest", "read"))
    return w, s, Caller(client, k)


# J — mesmo CNPJ => mesma Company
def test_same_cnpj_same_company(cc, db):
    _, _, c = cc
    c.ingest(ev("company.observed", company={"cnpj": "12.345.678/0001-99", "name": "ABC Ltda"},
                data={"key": "seg", "value": "logistica"}))
    c.ingest(ev("company.observed", company={"cnpj": "12345678000199", "name": "ABC Industria"}))
    assert db.execute(select(func.count()).select_from(Company)).scalar_one() == 1


# I — duas companies DIFERENTES podem compartilhar domain
def test_shared_domain_allowed(cc, db):
    _, _, c = cc
    c.ingest(ev("company.observed", company={"cnpj": "11111111000111", "domain": "grupo.com.br", "name": "Unidade A"}))
    c.ingest(ev("company.observed", company={"cnpj": "22222222000122", "domain": "grupo.com.br", "name": "Unidade B"}))
    assert db.execute(select(func.count()).select_from(Company)).scalar_one() == 2


def test_domain_resolves_when_single_candidate(cc, db):
    _, _, c = cc
    c.ingest(ev("company.observed", company={"domain": "solo.com", "name": "Solo"}))
    c.ingest(ev("company.observed", company={"domain": "solo.com"}))
    assert db.execute(select(func.count()).select_from(Company)).scalar_one() == 1


def test_ambiguous_domain_creates_case_no_merge(cc, db):
    _, _, c = cc
    # duas companies com o mesmo domínio (via CNPJs distintos)
    c.ingest(ev("company.observed", company={"cnpj": "33333333000133", "domain": "amb.com", "name": "A"}))
    c.ingest(ev("company.observed", company={"cnpj": "44444444000144", "domain": "amb.com", "name": "B"}))
    # agora um evento só com o domínio ambíguo
    c.ingest(ev("identity.observed", identities=email("z@amb.com"), company={"domain": "amb.com"}, event_id="amb-evt"))
    assert db.execute(select(func.count()).select_from(Company)).scalar_one() == 2  # NÃO fundiu
    cases = db.execute(
        select(ResolutionCase).where(ResolutionCase.case_type == "possible_duplicate_company")
    ).scalars().all()
    assert len(cases) == 1
    assert cases[0].details["ambiguous_on"] == "domain"
