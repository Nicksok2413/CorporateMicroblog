"""Интеграционные тесты для API эндпоинтов /users и подписок."""

import pytest
from httpx import AsyncClient
from fastapi import status

from app.models import User, Follow
from app.schemas import UserProfileResult, ResultTrue


# --- Тесты для GET /users/me ---

@pytest.mark.asyncio
async def test_get_current_user_profile_success(async_client: AsyncClient, test_user_alice: User, test_user_bob: User,
                                                alice_follows_bob: Follow):
    """Тест успешного получения своего профиля (включая подписки)."""
    headers = {"api-key": test_user_alice.api_key}
    response = await async_client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    profile = json_response["user"]
    assert profile["id"] == test_user_alice.id
    assert profile["name"] == test_user_alice.name

    # Проверяем подписки Алисы
    assert isinstance(profile["following"], list)
    found_bob_in_following = any(u["id"] == test_user_bob.id for u in profile["following"])
    assert found_bob_in_following

    # Проверяем подписчиков Алисы (пока пусто)
    assert isinstance(profile["followers"], list)
    # assert len(profile["followers"]) == 0 # Зависит от других фикстур


@pytest.mark.asyncio
async def test_get_current_user_profile_unauthorized(async_client: AsyncClient):
    """Тест получения своего профиля без ключа (ошибка 401)."""
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты для GET /users/{user_id} ---

@pytest.mark.asyncio
async def test_get_user_profile_by_id_success(async_client: AsyncClient, test_user_alice: User, test_user_bob: User,
                                              alice_follows_bob: Follow):
    """Тест успешного получения профиля другого пользователя."""
    # Запрос профиля Боба (Алиса подписана на него)
    response_bob = await async_client.get(f"/api/v1/users/{test_user_bob.id}")

    assert response_bob.status_code == status.HTTP_200_OK
    json_response_bob = response_bob.json()
    assert json_response_bob["result"] is True
    profile_bob = json_response_bob["user"]
    assert profile_bob["id"] == test_user_bob.id
    assert profile_bob["name"] == test_user_bob.name

    # Проверяем подписчиков Боба
    assert isinstance(profile_bob["followers"], list)
    found_alice_in_followers = any(u["id"] == test_user_alice.id for u in profile_bob["followers"])
    assert found_alice_in_followers


@pytest.mark.asyncio
async def test_get_user_profile_by_id_not_found(async_client: AsyncClient):
    """Тест получения профиля несуществующего пользователя (ошибка 404)."""
    non_existent_id = 99999
    response = await async_client.get(f"/api/v1/users/{non_existent_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


# --- Тесты для POST /users/{user_id}/follow ---

@pytest.mark.asyncio
async def test_follow_user_success(async_client: AsyncClient, test_user_alice: User, test_user_charlie: User):
    """Тест успешной подписки."""
    headers = {"api-key": test_user_alice.api_key}
    user_to_follow_id = test_user_charlie.id

    response = await async_client.post(f"/api/v1/users/{user_to_follow_id}/follow", headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True

    # Проверим профиль Алисы, что Чарли появился в подписках
    response_me = await async_client.get("/api/v1/users/me", headers=headers)
    profile_alice = response_me.json()["user"]
    found_charlie = any(u["id"] == user_to_follow_id for u in profile_alice["following"])
    assert found_charlie


@pytest.mark.asyncio
async def test_follow_user_already_following(async_client: AsyncClient, test_user_alice: User, test_user_bob: User,
                                             alice_follows_bob: Follow):
    """Тест повторной подписки (ошибка 409)."""
    headers = {"api-key": test_user_alice.api_key}  # Алиса уже подписана на Боба
    user_to_follow_id = test_user_bob.id

    response = await async_client.post(f"/api/v1/users/{user_to_follow_id}/follow", headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "conflict_error"


@pytest.mark.asyncio
async def test_follow_user_self(async_client: AsyncClient, test_user_alice: User):
    """Тест подписки на самого себя (ошибка 403)."""
    headers = {"api-key": test_user_alice.api_key}
    user_to_follow_id = test_user_alice.id

    response = await async_client.post(f"/api/v1/users/{user_to_follow_id}/follow", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "permission_denied"


@pytest.mark.asyncio
async def test_follow_user_not_found(async_client: AsyncClient, test_user_alice: User):
    """Тест подписки на несуществующего пользователя (ошибка 404)."""
    headers = {"api-key": test_user_alice.api_key}
    non_existent_id = 99999

    response = await async_client.post(f"/api/v1/users/{non_existent_id}/follow", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


# --- Тесты для DELETE /users/{user_id}/follow ---

@pytest.mark.asyncio
async def test_unfollow_user_success(async_client: AsyncClient, test_user_alice: User, test_user_bob: User,
                                     alice_follows_bob: Follow):
    """Тест успешной отписки."""
    headers = {"api-key": test_user_alice.api_key}  # Алиса подписана на Боба
    user_to_unfollow_id = test_user_bob.id

    response = await async_client.delete(f"/api/v1/users/{user_to_unfollow_id}/follow", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True

    # Проверим профиль Алисы, что Боба нет в подписках
    response_me = await async_client.get("/api/v1/users/me", headers=headers)
    profile_alice = response_me.json()["user"]
    found_bob = any(u["id"] == user_to_unfollow_id for u in profile_alice["following"])
    assert not found_bob


@pytest.mark.asyncio
async def test_unfollow_user_not_following(async_client: AsyncClient, test_user_alice: User, test_user_charlie: User):
    """Тест отписки от пользователя, на которого не подписан (ошибка 404)."""
    headers = {"api-key": test_user_alice.api_key}
    user_to_unfollow_id = test_user_charlie.id  # Алиса не подписана на Чарли

    response = await async_client.delete(f"/api/v1/users/{user_to_unfollow_id}/follow", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
