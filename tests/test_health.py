def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "stakeholder-intelligence-api"


def test_health_does_not_require_db(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
