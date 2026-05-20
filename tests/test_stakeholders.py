from unittest.mock import patch
from types import SimpleNamespace


def test_list_stakeholders_returns_paginated_result(client):
    contact = SimpleNamespace(
        contact_id="5511999999999",
        telefone="5511999999999",
        nome_atual="Cliente Teste",
        tipo_relacionamento="unknown",
        status_relacionamento="active",
        ultimo_contato_em=None,
        total_mensagens=12,
        score_oportunidade=0,
        score_risco=0,
        tags=["whatsapp"],
    )
    with patch("app.api.v1.endpoints.stakeholders.ContactRepository") as Repo:
        Repo.return_value.list.return_value = ([contact], 1)
        response = client.get("/api/v1/stakeholders?page=1&page_size=25&tag=whatsapp")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["contact_id"] == "5511999999999"


def test_list_stakeholders_validates_page_size(client):
    response = client.get("/api/v1/stakeholders?page_size=101")
    assert response.status_code == 422


def test_list_stakeholders_accepts_phone_suffix(client):
    with patch("app.api.v1.endpoints.stakeholders.ContactRepository") as Repo:
        Repo.return_value.list.return_value = ([], 0)
        response = client.get("/api/v1/stakeholders?q=99991253704")
    assert response.status_code == 200
    Repo.return_value.list.assert_called_once()
    assert Repo.return_value.list.call_args.kwargs["q"] == "99991253704"


def test_search_returns_empty_list(client):
    with patch("app.api.v1.endpoints.stakeholders.ContactRepository") as Repo:
        Repo.return_value.search.return_value = []
        response = client.get("/api/v1/stakeholders/search?q=nada")
    assert response.status_code == 200
    assert response.json() == []


def test_search_requires_q_param(client):
    response = client.get("/api/v1/stakeholders/search")
    assert response.status_code == 422


def test_get_stakeholder_404(client):
    with patch("app.api.v1.endpoints.stakeholders.ContactRepository") as Repo:
        Repo.return_value.get_by_id.return_value = None
        response = client.get("/api/v1/stakeholders/NONEXISTENT")
    assert response.status_code == 404


def test_get_conversations_empty(client):
    with patch("app.api.v1.endpoints.stakeholders.ConversationRepository") as Repo:
        Repo.return_value.get_by_contact_id.return_value = []
        response = client.get("/api/v1/stakeholders/c1/conversations")
    assert response.status_code == 200
    assert response.json() == []


def test_get_timeline_empty(client):
    with patch("app.api.v1.endpoints.stakeholders.TimelineRepository") as Repo:
        Repo.return_value.get_by_contact_id.return_value = []
        response = client.get("/api/v1/stakeholders/c1/timeline")
    assert response.status_code == 200
    assert response.json() == []


def test_get_opportunities_empty(client):
    with patch("app.api.v1.endpoints.stakeholders.OpportunityRepository") as Repo:
        Repo.return_value.get_by_contact_id.return_value = []
        response = client.get("/api/v1/stakeholders/c1/opportunities")
    assert response.status_code == 200
    assert response.json() == []
