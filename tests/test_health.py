"""Tests for health and basic HTTP endpoints."""


def test_health_returns_200(client):
    """GET /health should return 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_content_type(client):
    """Health endpoint should return JSON."""
    response = client.get("/health")
    assert response.content_type is not None
    assert "json" in response.content_type


def test_index_returns_200(client):
    """GET / should return 200."""
    response = client.get("/")
    assert response.status_code == 200
