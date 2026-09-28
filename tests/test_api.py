"""
API endpoint integration tests.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestLeaguesAPI:
    """Tests for leagues endpoints."""

    def test_list_leagues_empty(self):
        """Test listing leagues when empty."""
        response = client.get("/api/leagues")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_league_not_found(self):
        """Test getting non-existent league."""
        response = client.get("/api/leagues/999")
        assert response.status_code == 404


class TestFixturesAPI:
    """Tests for fixtures endpoints."""

    def test_list_fixtures_empty(self):
        """Test listing fixtures when empty."""
        response = client.get("/api/fixtures")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_fixtures_with_pagination(self):
        """Test fixtures pagination params."""
        response = client.get("/api/fixtures?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    def test_get_fixture_not_found(self):
        """Test getting non-existent fixture."""
        response = client.get("/api/fixtures/999")
        assert response.status_code == 404

    def test_get_fixture_by_external_not_found(self):
        """Test getting fixture by non-existent external ID."""
        response = client.get("/api/fixtures/external/NONEXISTENT")
        assert response.status_code == 404


class TestTeamsAPI:
    """Tests for teams endpoints."""

    def test_list_teams_empty(self):
        """Test listing teams when empty."""
        response = client.get("/api/teams")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestOddsAPI:
    """Tests for odds endpoints."""

    def test_list_odds_empty(self):
        """Test listing odds for fixture when empty."""
        response = client.get("/api/odds/fixture/999")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_preflight(self):
        """Test CORS preflight request."""
        response = client.options(
            "/api/leagues",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_headers(self):
        """Test CORS headers on regular request."""
        response = client.get(
            "/api/leagues",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
