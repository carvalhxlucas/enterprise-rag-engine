import pytest

from app.main import create_app


@pytest.mark.unit
class TestCreateApp:
    def test_returns_fastapi_instance(self):
        app = create_app()
        assert app.title == "Enterprise RAG Engine"

    def test_health_route_exists(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
