import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Follow  # Нужны для проверок и типизации
from src.core.config import settings  # Нужен API_KEY_HEADER

pytestmark = pytest.mark.asyncio


# === GET /api/users/me ===

async def test_get_my_profile_unauthorized(client: AsyncClient):
    response = await client.get("/api/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_my_profile_invalid_key(client: AsyncClient):
    headers = {settings.API_KEY_HEADER: "invalid-key"}
    response = await client.get("/api/users/me", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_get_my_profile_success(authenticated_client: AsyncClient, test_user: User):
    response = await authenticated_client.get("/api/users/me")
    assert response.status_code == status.HTTP_200_OK
    profile = response.json()["user"]
    assert profile["id"] == test_user.id
    assert profile["name"] == test_user.name
    assert profile["followers"] == []
    assert profile["following"] == []


# === GET /api/users/{user_id} ===

async def test_get_user_profile_by_id_not_found(client: AsyncClient):
    response = await client.get("/api/users/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_user_profile_by_id_success(client: AsyncClient, test_user_alice: User):
    response = await client.get(f"/api/users/{test_user_alice.id}")
    assert response.status_code == status.HTTP_200_OK
    profile = response.json()["user"]
    assert profile["id"] == test_user_alice.id
    assert profile["name"] == test_user_alice.name
    assert "followers" in profile
    assert "following" in profile


# === POST /api/users/{user_id}/follow ===

async def test_follow_user_unauthorized(client: AsyncClient, test_user_alice: User):
    response = await client.post(f"/api/users/{test_user_alice.id}/follow")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_follow_user_self(authenticated_client: AsyncClient, test_user: User):
    response = await authenticated_client.post(f"/api/users/{test_user.id}/follow")
    assert response.status_code == status.HTTP_403_FORBIDDEN  # Используем PermissionDeniedError


async def test_follow_non_existent_user(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/users/9999/follow")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_follow_user_success(authenticated_client: AsyncClient, test_user: User, test_user_alice: User,
                                   db_session: AsyncSession):
    response = await authenticated_client.post(f"/api/users/{test_user_alice.id}/follow")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["result"] is True

    # Проверяем в БД (хотя можно и через API профиля)
    await db_session.refresh(test_user, attribute_names=['following'])
    await db_session.refresh(test_user_alice, attribute_names=['followers'])
    follow_relation = await db_session.get(Follow, (test_user.id, test_user_alice.id))
    assert follow_relation is not None
    assert follow_relation.follower_id == test_user.id
    assert follow_relation.following_id == test_user_alice.id

    # Проверка через API
    response_me = await authenticated_client.get("/api/users/me")
    following_list = response_me.json()["user"]["following"]
    assert len(following_list) == 1
    assert following_list[0]["id"] == test_user_alice.id

    response_alice = await authenticated_client.get(f"/api/users/{test_user_alice.id}")
    followers_list = response_alice.json()["user"]["followers"]
    assert len(followers_list) == 1
    assert followers_list[0]["id"] == test_user.id


async def test_follow_user_already_followed(authenticated_client: AsyncClient, test_user_alice: User):
    # Сначала подписываемся
    await authenticated_client.post(f"/api/users/{test_user_alice.id}/follow")
    # Пытаемся подписаться снова
    response = await authenticated_client.post(f"/api/users/{test_user_alice.id}/follow")
    assert response.status_code == status.HTTP_409_CONFLICT


# === DELETE /api/users/{user_id}/follow ===

async def test_unfollow_user_unauthorized(client: AsyncClient, test_user_alice: User):
    response = await client.delete(f"/api/users/{test_user_alice.id}/follow")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unfollow_user_self(authenticated_client: AsyncClient, test_user: User):
    response = await authenticated_client.delete(f"/api/users/{test_user.id}/follow")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_unfollow_non_existent_user(authenticated_client: AsyncClient):
    response = await authenticated_client.delete("/api/users/9999/follow")
    assert response.status_code == status.HTTP_404_NOT_FOUND  # Проверка на существование пользователя


async def test_unfollow_user_not_followed(authenticated_client: AsyncClient, test_user_alice: User):
    # Убедимся, что не подписаны
    response = await authenticated_client.delete(f"/api/users/{test_user_alice.id}/follow")
    assert response.status_code == status.HTTP_404_NOT_FOUND  # Ошибка от сервиса "подписка не найдена"


async def test_unfollow_user_success(authenticated_client: AsyncClient, test_user_alice: User,
                                     db_session: AsyncSession):
    # Сначала подписываемся
    await authenticated_client.post(f"/api/users/{test_user_alice.id}/follow")
    # Теперь отписываемся
    response = await authenticated_client.delete(f"/api/users/{test_user_alice.id}/follow")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"] is True

    # Проверяем в БД
    follow_relation = await db_session.get(Follow, (test_user.id, test_user_alice.id))
    assert follow_relation is None

    # Проверка через API
    response_me = await authenticated_client.get("/api/users/me")
    assert len(response_me.json()["user"]["following"]) == 0
