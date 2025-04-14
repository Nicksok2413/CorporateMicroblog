import pytest
from httpx import AsyncClient
from fastapi import status

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


async def test_read_root(client: AsyncClient):
    """Тестирует корневой эндпоинт '/'."""
    response = await client.get("/")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["message"] == "Добро пожаловать в Microblog Service!"
    assert json_response["status"] == "operational"
    # Проверяем, что debug_mode = False, так как TESTING=True
    assert json_response["debug_mode"] is False
