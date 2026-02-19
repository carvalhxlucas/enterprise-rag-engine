import pytest
from fastapi import Header

from app.core.security import get_current_user_id


@pytest.mark.unit
class TestGetCurrentUserId:
    @pytest.mark.asyncio
    async def test_returns_x_user_id_header_value(self):
        result = await get_current_user_id(x_user_id="user-123")
        assert result == "user-123"

    @pytest.mark.asyncio
    async def test_returns_whatever_value_passed(self):
        result = await get_current_user_id(x_user_id="admin-456")
        assert result == "admin-456"
