from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.stack360.models.ingestion_event import IngestionEvent
from app.stack360.models.person import Person, PersonIdentity
from app.stack360.models.resolution import ResolutionCase
from tests.stack360._helpers import Caller, email, ev


@pytest.fixture()
def setup(client, make_workspace, make_source, make_api_key):
    w = make_workspace()
    s1 = make_source(w, key="src-a")
    s2 = make_source(w, key="src-b")
    k1, _ = make_api_key(w, s1, scopes=("ingest", "read"))
    k2, _ = make_api_key(w, s2, scopes=("ingest", "read"))
    return w, s1, s2, Caller(client, k1), Caller(client, k2)


def test_zero_match_creates_person(setup, db):
    *_, a, _ = setup
    r = a.ingest(ev("identity.observed", identities=email("new@x.com")))
    assert r.status_code == 200
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 1


def test_one_match_reuses_person(setup, db):
    *_, a, _ = setup
    a.ingest(ev("identity.observed", identities=email("same@x.com")))
    a.ingest(ev("identity.observed", identities=email("same@x.com") + [{"type": "phone", "value": "+5511999998888"}]))
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 1
    assert db.execute(select(func.count()).select_from(PersonIdentity)).scalar_one() == 2


# E — source A + source B mesmo email => MESMA Person
def test_unification_same_email_two_sources(setup, db):
    _, _, _, a, b = setup
    r1 = a.ingest(ev("identity.observed", identities=email("carlos@empresa.com")))
    r2 = b.ingest(ev("identity.observed", identities=email("carlos@empresa.com")))
    assert r1.json()["entities"]["person_id"] == r2.json()["entities"]["person_id"]
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 1


# F/G — instagram/linkedin handle igual em sources diferentes NÃO faz merge global
@pytest.mark.parametrize("itype", ["instagram", "linkedin"])
def test_social_handles_are_source_scoped(setup, db, itype):
    _, _, _, a, b = setup
    a.ingest(ev("identity.observed", identities=[{"type": itype, "value": "@joe"}]))
    b.ingest(ev("identity.observed", identities=[{"type": itype, "value": "@joe"}]))
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 2


# visitor_id igual em sources diferentes NÃO colide
def test_visitor_id_source_scoped(setup, db):
    _, _, _, a, b = setup
    a.ingest(ev("identity.observed", identities=[{"type": "visitor_id", "value": "v-1"}]))
    b.ingest(ev("identity.observed", identities=[{"type": "visitor_id", "value": "v-1"}]))
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 2


# H — phone e whatsapp que resolvem ao mesmo E.164 => MESMA Person
def test_phone_and_whatsapp_same_e164(setup, db):
    *_, a, _ = setup
    r1 = a.ingest(ev("identity.observed", identities=[{"type": "phone", "value": "+55 11 98888-7777"}]))
    r2 = a.ingest(ev("identity.observed", identities=[{"type": "whatsapp", "value": "5511988887777"}]))
    assert r1.json()["entities"]["person_id"] == r2.json()["entities"]["person_id"]
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 1


# B/C — IDENTITY_CONFLICT: raw preservado + status conflict + exatamente 1 resolution_case
def test_identity_conflict(setup, db):
    *_, a, _ = setup
    # duas Persons distintas
    a.ingest(ev("identity.observed", identities=email("p1@x.com")))
    a.ingest(ev("identity.observed", identities=[{"type": "phone", "value": "+5511900000001"}]))
    assert db.execute(select(func.count()).select_from(Person)).scalar_one() == 2

    r = a.ingest(
        ev(
            "identity.observed",
            identities=email("p1@x.com") + [{"type": "phone", "value": "+5511900000001"}],
            event_id="conflict-evt",
        )
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "IDENTITY_CONFLICT"

    ie = db.execute(
        select(IngestionEvent).where(IngestionEvent.external_event_id == "conflict-evt")
    ).scalar_one()
    assert ie.status == "conflict"  # raw SOBREVIVE
    cases = db.execute(
        select(ResolutionCase).where(ResolutionCase.ingestion_event_id == ie.id)
    ).scalars().all()
    assert len(cases) == 1 and cases[0].case_type == "identity_conflict"

    # D — replay do mesmo conflito NÃO duplica o caso
    r2 = a.ingest(
        ev(
            "identity.observed",
            identities=email("p1@x.com") + [{"type": "phone", "value": "+5511900000001"}],
            event_id="conflict-evt",
        )
    )
    assert r2.status_code == 409
    cases = db.execute(
        select(ResolutionCase).where(ResolutionCase.ingestion_event_id == ie.id)
    ).scalars().all()
    assert len(cases) == 1
