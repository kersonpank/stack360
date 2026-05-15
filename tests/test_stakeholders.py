from unittest.mock import patch


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
