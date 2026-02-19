import pytest


@pytest.mark.unit
class TestDocumentsRouter:
    def test_list_documents_returns_200_and_empty_list(self, client):
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert data["documents"] == []
