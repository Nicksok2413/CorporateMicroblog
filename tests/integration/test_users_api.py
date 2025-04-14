import pytest
from httpx import AsyncClient
from fastapi import status

from src.models import User  # Нужен для типизации фикстуры

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


async def test_get_my_profile_unauthorized(client: AsyncClient):
    """Тест получения профиля без api-key."""
    response = await client.get("/api/users/me")
    # Ожидаем ошибку 401 Unauthorized (согласно нашей зависимости get_current_user)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "unauthorized"


async def test_get_my_profile_invalid_key(client: AsyncClient):
    """Тест получения профиля с неверным api-key."""
    headers = {"api-key": "invalid-key"}
    response = await client.get("/api/users/me", headers=headers)
    # Ожидаем ошибку 403 Forbidden (согласно нашей зависимости get_current_user)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "permission_denied"
    assert "Недействительный API ключ" in json_response["error_message"]


async def test_get_my_profile_success(
        authenticated_client: AsyncClient,  # Используем фикстуру с ключом
        test_user: User  # Получаем тестового пользователя для сравнения
):
    """Тест успешного получения своего профиля."""
    response = await authenticated_client.get("/api/users/me")

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    profile = json_response["user"]
    assert profile["id"] == test_user.id
    assert profile["name"] == test_user.name
    assert profile["followers"] == []  # Пока нет подписчиков в этом тесте
    assert profile["following"] == []  # Пока нет подписок


async def test_get_user_profile_by_id_not_found(client: AsyncClient):
    """Тест получения профиля несуществующего пользователя по ID."""
    response = await client.get("/api/users/9999")  # Заведомо несуществующий ID
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


async def test_get_user_profile_by_id_success(
        client: AsyncClient,  # Обычный клиент, аутентификация не нужна
        test_user: User
):
    """Тест успешного получения профиля существующего пользователя по ID."""
    response = await client.get(f"/api/users/{test_user.id}")

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    profile = json_response["user"]
    assert profile["id"] == test_user.id
    assert profile["name"] == test_user.name
    assert "followers" in profile
    assert "following" in profile

# TODO: Добавить тесты для follow/unfollow
