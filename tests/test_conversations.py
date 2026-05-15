from unittest.mock import patch


def test_get_messages_paginated_response(client):
    with patch("app.api.v1.endpoints.conversations.MessageRepository") as Repo:
        Repo.return_value.get_by_conversation_id.return_value = ([], 0)
        response = client.get("/api/v1/conversations/conv123/messages")
    assert response.status_code == 200
    data = response.json()
    assert data == {"total": 0, "limit": 100, "offset": 0, "items": []}


def test_get_messages_rejects_limit_above_500(client):
    response = client.get("/api/v1/conversations/conv123/messages?limit=501")
    assert response.status_code == 422


def test_get_messages_rejects_invalid_order(client):
    response = client.get("/api/v1/conversations/conv123/messages?order=random")
    assert response.status_code == 422


def test_get_messages_accepts_desc_order(client):
    with patch("app.api.v1.endpoints.conversations.MessageRepository") as Repo:
        Repo.return_value.get_by_conversation_id.return_value = ([], 0)
        response = client.get("/api/v1/conversations/conv123/messages?order=desc&limit=50&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 50 and data["offset"] == 10
