from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestChatRouter:
    def test_chat_stream_requires_x_user_id_header(self, client):
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "hello", "history": [], "config": {}},
        )
        assert response.status_code == 422

    def test_chat_stream_returns_streaming_response_with_user_id(self, client):
        with patch("app.api.v1.routers.chat.ChatOrchestrator") as mock_orchestrator:
            mock_instance = MagicMock()
            mock_instance.stream_chat.return_value = (chunk for chunk in [b"data: ok\n\n"])
            mock_orchestrator.return_value = mock_instance
            response = client.post(
                "/api/v1/chat/stream",
                headers={"X-User-ID": "test-user"},
                json={
                    "message": "hello",
                    "history": [],
                    "config": {"persona": "technical", "temperature": 0.7, "use_hybrid_search": True},
                },
            )
            assert response.status_code == 200
            assert response.headers.get("content-type", "").startswith("text/event-stream")
