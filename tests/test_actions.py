import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/testdb")
os.environ.setdefault("API_ENV", "testing")
os.environ["NORMALIZER_SCHEDULER_ENABLED"] = "false"
os.environ["ENRICHMENT_SCHEDULER_ENABLED"] = "false"

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.action_service import _collect_rules, ActionService


# -----------------------------------------------------------------------
# Helpers — plain namespaces avoid SQLAlchemy mapper init
# -----------------------------------------------------------------------

def _contact(**kwargs) -> SimpleNamespace:
    defaults = dict(
        contact_id="5511000000001",
        nome_atual="Test",
        tipo_relacionamento="lead",
        score_oportunidade=Decimal(50),
        score_risco=Decimal(0),
        total_mensagens=10,
        tags=["whatsapp"],
        resumo_geral=None,
        ultimo_contato_em=datetime.now(tz=timezone.utc) - timedelta(days=5),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _opportunity(**kwargs) -> SimpleNamespace:
    defaults = dict(
        opportunity_id=1,
        contact_id="5511000000001",
        tipo_oportunidade="cotacao_frete",
        status="nova",
        score=Decimal(60),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# -----------------------------------------------------------------------
# Rule 1: followup_cotacao
# -----------------------------------------------------------------------

def test_followup_cotacao_generated():
    contact = _contact()
    opp = _opportunity(tipo_oportunidade="cotacao_frete", status="nova")
    actions = _collect_rules(contact, [opp], [])
    types = [a["action_type"] for a in actions]
    assert "followup_cotacao" in types


def test_followup_cotacao_not_generated_without_open_opp():
    contact = _contact()
    opp = _opportunity(tipo_oportunidade="cotacao_frete", status="concluida")
    actions = _collect_rules(contact, [opp], [])
    types = [a["action_type"] for a in actions]
    assert "followup_cotacao" not in types


def test_followup_cotacao_not_generated_different_type():
    contact = _contact()
    opp = _opportunity(tipo_oportunidade="motorista_parceiro", status="nova")
    actions = _collect_rules(contact, [opp], [])
    types = [a["action_type"] for a in actions]
    assert "followup_cotacao" not in types


# -----------------------------------------------------------------------
# Rule 2: qualificar_motorista
# -----------------------------------------------------------------------

def test_qualificar_motorista_incomplete_profile():
    contact = _contact(tipo_relacionamento="motorista")
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "qualificar_motorista" in types


def test_qualificar_motorista_not_generated_when_complete():
    contact = _contact(tipo_relacionamento="motorista")
    full_evidence = ["cidade_base", "rota", "veiculo", "carroceria", "veiculo_tipo", "tipo_veiculo"]
    actions = _collect_rules(contact, [], full_evidence)
    types = [a["action_type"] for a in actions]
    assert "qualificar_motorista" not in types


def test_qualificar_motorista_not_generated_for_lead():
    contact = _contact(tipo_relacionamento="lead")
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "qualificar_motorista" not in types


# -----------------------------------------------------------------------
# Rule 3: convidar_motorista_para_plataforma
# -----------------------------------------------------------------------

def test_convidar_motorista_from_fretebras_tag():
    contact = _contact(tags=["whatsapp", "fretebras"])
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "convidar_motorista_para_plataforma" in types


def test_convidar_motorista_from_motorista_parceiro_opp():
    contact = _contact()
    opp = _opportunity(tipo_oportunidade="motorista_parceiro", status="nova")
    actions = _collect_rules(contact, [opp], [])
    types = [a["action_type"] for a in actions]
    assert "convidar_motorista_para_plataforma" in types


def test_convidar_motorista_min_priority_70():
    contact = _contact(score_oportunidade=Decimal(20), tags=["whatsapp", "fretebras"])
    actions = _collect_rules(contact, [], [])
    action = next(a for a in actions if a["action_type"] == "convidar_motorista_para_plataforma")
    assert action["priority_score"] >= 70


def test_convidar_motorista_not_generated_without_signal():
    contact = _contact(tags=["whatsapp"])
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "convidar_motorista_para_plataforma" not in types


# -----------------------------------------------------------------------
# Rule 4: pedir_cnpj
# -----------------------------------------------------------------------

def test_pedir_cnpj_lead_without_cnpj():
    contact = _contact(tipo_relacionamento="lead")
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "pedir_cnpj" in types


def test_pedir_cnpj_not_generated_when_cnpj_exists():
    contact = _contact(tipo_relacionamento="lead")
    actions = _collect_rules(contact, [], ["cnpj"])
    types = [a["action_type"] for a in actions]
    assert "pedir_cnpj" not in types


def test_pedir_cnpj_from_commercial_tag():
    contact = _contact(tipo_relacionamento="motorista", tags=["whatsapp", "frete"])
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "pedir_cnpj" in types


# -----------------------------------------------------------------------
# Rule 5: completar_dados_comerciais
# -----------------------------------------------------------------------

def test_completar_dados_comerciais_lead_with_resumo():
    contact = _contact(tipo_relacionamento="lead", resumo_geral="Resumo do lead.")
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "completar_dados_comerciais" in types


def test_completar_dados_comerciais_not_without_resumo():
    contact = _contact(tipo_relacionamento="lead", resumo_geral=None)
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "completar_dados_comerciais" not in types


# -----------------------------------------------------------------------
# Rule 6: reativar_contato
# -----------------------------------------------------------------------

def test_reativar_contato_high_score_old_contact():
    old_date = datetime.now(tz=timezone.utc) - timedelta(days=90)
    contact = _contact(score_oportunidade=Decimal(70), ultimo_contato_em=old_date)
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "reativar_contato" in types


def test_reativar_contato_not_for_recent_contact():
    recent = datetime.now(tz=timezone.utc) - timedelta(days=10)
    contact = _contact(score_oportunidade=Decimal(70), ultimo_contato_em=recent)
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "reativar_contato" not in types


def test_reativar_contato_not_for_low_score():
    old_date = datetime.now(tz=timezone.utc) - timedelta(days=90)
    contact = _contact(score_oportunidade=Decimal(30), ultimo_contato_em=old_date)
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "reativar_contato" not in types


# -----------------------------------------------------------------------
# Rule 7: revisar_alto_potencial
# -----------------------------------------------------------------------

def test_revisar_alto_potencial_score_80():
    contact = _contact(score_oportunidade=Decimal(80))
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "revisar_alto_potencial" in types


def test_revisar_alto_potencial_score_100():
    contact = _contact(score_oportunidade=Decimal(100))
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "revisar_alto_potencial" in types


def test_revisar_alto_potencial_not_for_score_79():
    contact = _contact(score_oportunidade=Decimal(79))
    actions = _collect_rules(contact, [], [])
    types = [a["action_type"] for a in actions]
    assert "revisar_alto_potencial" not in types


# -----------------------------------------------------------------------
# ActionService: dry-run does not write
# -----------------------------------------------------------------------

def test_dry_run_does_not_write():
    read_db = MagicMock()
    write_db = MagicMock()

    contact = _contact()
    opp = _opportunity()

    with patch("app.services.action_service.ActionRepository") as MockRepo:
        repo_instance = MagicMock()
        MockRepo.return_value = repo_instance
        repo_instance.get_contacts_for_action_generation.return_value = [contact]
        repo_instance.get_open_opportunities_for_contact.return_value = [opp]
        repo_instance.get_evidence_types_for_contact.return_value = []
        repo_instance.get_open_action.return_value = None

        svc = ActionService(read_db=read_db, write_db=write_db)
        result = svc.run(limit=10, dry_run=True)

    repo_instance.upsert_action.assert_not_called()
    write_db.commit.assert_not_called()
    assert result["dry_run"] is True


# -----------------------------------------------------------------------
# ActionService: no duplicate for open action
# -----------------------------------------------------------------------

def test_upsert_updates_existing_open_action():
    read_db = MagicMock()
    write_db = MagicMock()

    contact = _contact(score_oportunidade=Decimal(80))
    existing_action = MagicMock()

    with patch("app.services.action_service.ActionRepository") as MockRepo:
        repo_instance = MagicMock()
        MockRepo.return_value = repo_instance
        repo_instance.get_contacts_for_action_generation.return_value = [contact]
        repo_instance.get_open_opportunities_for_contact.return_value = []
        repo_instance.get_evidence_types_for_contact.return_value = []
        repo_instance.get_open_action.return_value = existing_action
        repo_instance.upsert_action.return_value = "updated"

        svc = ActionService(read_db=read_db, write_db=write_db)
        result = svc.run(limit=10, dry_run=False)

    assert result["actions_updated"] > 0


# -----------------------------------------------------------------------
# API endpoints (mock DB)
# -----------------------------------------------------------------------

def test_get_actions_endpoint(client):
    with patch("app.repositories.action_repository.ActionRepository.get_actions") as mock_get:
        mock_get.return_value = []
        resp = client.get("/api/v1/actions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_actions_summary_endpoint(client):
    with patch("app.repositories.action_repository.ActionRepository.get_summary") as mock_sum:
        mock_sum.return_value = {
            "total_actions": 0,
            "novas": 0,
            "em_andamento": 0,
            "concluidas": 0,
            "descartadas": 0,
            "by_action_type": {},
            "top_priority": [],
        }
        resp = client.get("/api/v1/actions/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_actions" in data
    assert "by_action_type" in data


def test_get_stakeholder_actions_endpoint(client):
    with patch("app.repositories.action_repository.ActionRepository.get_actions_for_contact") as mock_ac:
        mock_ac.return_value = []
        resp = client.get("/api/v1/stakeholders/5511000000001/actions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_patch_action_status_invalid(client):
    resp = client.patch("/api/v1/actions/999/status", json={"status": "invalido"})
    assert resp.status_code == 422


def test_get_system_action_status_endpoint(client):
    with patch("app.repositories.action_repository.ActionRepository.get_action_system_status") as mock_s:
        mock_s.return_value = {
            "total_actions": 5,
            "pending_actions": 3,
            "actions_by_type": {"followup_cotacao": 2},
            "actions_by_status": {"nova": 3},
            "last_generated_at": None,
        }
        resp = client.get("/api/v1/system/action-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_actions"] == 5
    assert data["pending_actions"] == 3
