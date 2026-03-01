"""Tests for main routes (no AI/email side effects)."""


def test_positions_list_returns_200(client):
    """GET /positions should return 200."""
    response = client.get("/positions")
    assert response.status_code == 200


def test_tickets_list_returns_200(client):
    """GET /tickets should return 200."""
    response = client.get("/tickets")
    assert response.status_code == 200


def test_admin_returns_200(client):
    """GET /admin should return 200."""
    response = client.get("/admin")
    assert response.status_code == 200


def test_metrics_returns_200(client):
    """GET /metrics should return 200."""
    response = client.get("/metrics")
    assert response.status_code == 200


def test_add_candidate_form_returns_200(client):
    """GET /add_candidate should return 200."""
    response = client.get("/add_candidate")
    assert response.status_code == 200


def test_add_position_form_returns_200(client):
    """GET /positions/add should return 200."""
    response = client.get("/positions/add")
    assert response.status_code == 200


def test_candidates_index_returns_200(client):
    """GET / (candidates list) should return 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_candidate_detail_not_found_redirects(client):
    """GET /candidate/999999 (non-existent) should redirect to index with flash."""
    response = client.get("/candidate/999999")
    assert response.status_code in (302, 200)
    if response.status_code == 302:
        assert "index" in response.location or response.location.endswith("/")
