"""Tests for health and basic HTTP endpoints."""

from unittest.mock import patch


def test_health_returns_200(client):
    """GET /health should return 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_content_type(client):
    """Health endpoint should return JSON."""
    response = client.get("/health")
    assert response.content_type is not None
    assert "json" in response.content_type


def test_health_json_has_expected_structure(client):
    """Health JSON should contain status or similar key."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert isinstance(data, dict)


def test_index_returns_200(client):
    """GET / should return 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_health_returns_503_when_db_fails(client):
    """When DB check fails, health should return 503 and unhealthy."""
    with patch("routes.health.get_db") as mock_get_db:
        mock_get_db.return_value.execute.side_effect = Exception("DB connection failed")
        response = client.get("/health")
    assert response.status_code == 503
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "unhealthy"
    assert "error" in data or "DB" in str(data.get("error", ""))
