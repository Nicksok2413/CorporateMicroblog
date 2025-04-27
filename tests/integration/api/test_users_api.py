from typing import Tuple

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models import Follow, User

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тесты для /api/users/me ---


async def test_get_my_profile_unauthorized(client: AsyncClient):
    """Тест получения профиля /me без api-key."""
    response = await client.get("/api/users/me")

    # Проверки
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "unauthorized"


async def test_get_my_profile_invalid_key(client: AsyncClient):
    """Тест получения профиля /me с неверным api-key."""
    headers = {settings.API_KEY_HEADER: "invalid-key"}

    response = await client.get("/api/users/me", headers=headers)

    # Проверки
    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "permission_denied"
    assert "Недействительный API ключ" in json_response["error_message"]


async def test_get_my_profile_success(
    authenticated_client: AsyncClient, test_user_data: Tuple[User, str]
):
    """Тест успешного получения своего профиля /me."""
    test_user, _ = test_user_data

    response = await authenticated_client.get("/api/users/me")

    # Проверки
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    profile = json_response["user"]
    assert profile["id"] == test_user.id
    assert profile["name"] == test_user.name
    # Проверяем наличие подписчиков и подписок, списки должны быть пустыми по умолчанию
    assert "followers" in profile
    assert profile["followers"] == []
    assert "following" in profile
    assert profile["following"] == []


# --- Тесты для /api/users/{user_id} ---


async def test_get_user_profile_by_id_success(
    authenticated_client: AsyncClient, test_user_alice_data: Tuple[User, str]
):
    """Тест успешного получения своего профиля /me."""
    test_user_alice, _ = test_user_alice_data

    response = await authenticated_client.get(f"/api/users/{test_user_alice.id}")

    # Проверки
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    profile = json_response["user"]
    assert profile["id"] == test_user_alice.id
    assert profile["name"] == test_user_alice.name
    # Проверяем наличие подписчиков и подписок, списки должны быть пустыми по умолчанию
    assert "followers" in profile
    assert profile["followers"] == []
    assert "following" in profile
    assert profile["following"] == []


async def test_get_user_profile_by_id_not_found(client: AsyncClient):
    """Тест получения профиля несуществующего пользователя по ID."""
    response = await client.get("/api/users/9999")

    # Проверки
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


async def test_get_user_profile_with_follows_by_id_success(
    client: AsyncClient,
    test_user_data: Tuple[User, str],
    test_user_alice_data: Tuple[User, str],
    db_session: AsyncSession,
):
    """Тест успешного получения профиля пользователя по ID с подписчиками/подписками."""
    test_user, _ = test_user_data
    test_user_alice, _ = test_user_alice_data

    # Создаем подписки: alice -> test_user, test_user -> alice
    follow1 = Follow(follower_id=test_user_alice.id, following_id=test_user.id)
    follow2 = Follow(follower_id=test_user.id, following_id=test_user_alice.id)
    db_session.add_all([follow1, follow2])
    await db_session.commit()

    # Запрашиваем профиль test_user
    response = await client.get(f"/api/users/{test_user.id}")

    # Проверки
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    profile = json_response["user"]
    assert profile["id"] == test_user.id
    assert profile["name"] == test_user.name

    # Проверяем подписчиков (followers) - должен быть alice
    assert len(profile["followers"]) == 1
    assert profile["followers"][0]["id"] == test_user_alice.id
    assert profile["followers"][0]["name"] == test_user_alice.name

    # Проверяем подписки (following) - должен быть alice
    assert len(profile["following"]) == 1
    assert profile["following"][0]["id"] == test_user_alice.id
    assert profile["following"][0]["name"] == test_user_alice.name


# --- Тесты для POST /api/users/{user_id}/follow ---


async def test_follow_user_unauthorized(
    client: AsyncClient, test_user_alice_data: Tuple[User, str]
):
    """Тест подписки без авторизации."""
    test_user_alice, _ = test_user_alice_data

    response = await client.post(f"/api/users/{test_user_alice.id}/follow")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_follow_user_invalid_key(
    client: AsyncClient, test_user_alice_data: Tuple[User, str]
):
    """Тест подписки с неверным ключом."""
    test_user_alice, _ = test_user_alice_data
    headers = {settings.API_KEY_HEADER: "invalid-key"}

    response = await client.post(
        f"/api/users/{test_user_alice.id}/follow", headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_follow_user_self(
    authenticated_client: AsyncClient, test_user_data: Tuple[User, str]
):
    """Тест попытки подписаться на себя."""
    test_user, _ = test_user_data

    response = await authenticated_client.post(f"/api/users/{test_user.id}/follow")

    # Проверки
    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["error_type"] == "permission_denied"
    assert "Вы не можете подписаться на себя" in json_response["error_message"]


async def test_follow_user_not_found(authenticated_client: AsyncClient):
    """Тест попытки подписаться на несуществующего пользователя."""
    response = await authenticated_client.post("/api/users/9999/follow")

    # Проверки
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["error_type"] == "not_found"
    assert "Пользователь с ID 9999 не найден" in json_response["error_message"]


async def test_follow_user_success(
    authenticated_client: AsyncClient,
    test_user_data: Tuple[User, str],
    test_user_alice_data: Tuple[User, str],
    db_session: AsyncSession,
):
    """Тест успешной подписки."""
    test_user, _ = test_user_data
    test_user_alice, _ = test_user_alice_data

    response = await authenticated_client.post(
        f"/api/users/{test_user_alice.id}/follow"
    )

    # Проверки
    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем запись в БД
    follow_rel = await db_session.execute(
        select(Follow).where(
            Follow.follower_id == test_user.id,
            Follow.following_id == test_user_alice.id,
        )
    )

    assert follow_rel.scalar_one_or_none() is not None

    # Проверка через API
    response_me = await authenticated_client.get("/api/users/me")
    following_list = response_me.json()["user"]["following"]
    assert len(following_list) == 1
    assert following_list[0]["id"] == test_user_alice.id

    response_alice = await authenticated_client.get(f"/api/users/{test_user_alice.id}")
    followers_list = response_alice.json()["user"]["followers"]
    assert len(followers_list) == 1
    assert followers_list[0]["id"] == test_user.id


async def test_follow_user_already_followed(
    authenticated_client: AsyncClient,
    test_user_data: Tuple[User, str],
    test_user_alice_data: Tuple[User, str],
    db_session: AsyncSession,
):
    """Тест попытки повторной подписки."""
    test_user, _ = test_user_data
    test_user_alice, _ = test_user_alice_data

    # Сначала подписываемся
    follow = Follow(follower_id=test_user.id, following_id=test_user_alice.id)
    db_session.add(follow)
    await db_session.commit()

    # Пытаемся подписаться снова через API
    response = await authenticated_client.post(
        f"/api/users/{test_user_alice.id}/follow"
    )

    # Проверки
    assert response.status_code == status.HTTP_409_CONFLICT
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "conflict_error"
    assert "Вы уже подписаны" in json_response["error_message"]


# --- Тесты для DELETE /api/users/{user_id}/follow ---


async def test_unfollow_user_unauthorized(
    client: AsyncClient, test_user_alice_data: Tuple[User, str]
):
    """Тест отписки без авторизации."""
    test_user_alice, _ = test_user_alice_data

    response = await client.delete(f"/api/users/{test_user_alice.id}/follow")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unfollow_user_invalid_key(
    client: AsyncClient, test_user_alice_data: Tuple[User, str]
):
    """Тест отписки с неверным ключом."""
    test_user_alice, _ = test_user_alice_data
    headers = {settings.API_KEY_HEADER: "invalid-key"}

    response = await client.delete(
        f"/api/users/{test_user_alice.id}/follow", headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_unfollow_user_self(
    authenticated_client: AsyncClient, test_user_data: Tuple[User, str]
):
    """Тест попытки отписаться от себя."""
    test_user, _ = test_user_data

    response = await authenticated_client.delete(f"/api/users/{test_user.id}/follow")

    assert (
        response.status_code == status.HTTP_403_FORBIDDEN
    )  # Ошибка валидации в сервисе

    # Проверки
    json_response = response.json()
    assert json_response["error_type"] == "permission_denied"
    assert (
        "Вы не можете подписаться на себя" in json_response["error_message"]
    )  # Сообщение из _validate_follow_action


async def test_unfollow_user_not_found_target(authenticated_client: AsyncClient):
    """Тест попытки отписаться от несуществующего пользователя."""
    response = await authenticated_client.delete("/api/users/9999/follow")

    # Проверки
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["error_type"] == "not_found"
    assert "Пользователь с ID 9999 не найден" in json_response["error_message"]


async def test_unfollow_user_not_following(
    authenticated_client: AsyncClient, test_user_alice_data: Tuple[User, str]
):
    """Тест попытки отписаться от пользователя, на которого не подписан."""
    test_user_alice, _ = test_user_alice_data

    response = await authenticated_client.delete(
        f"/api/users/{test_user_alice.id}/follow"
    )

    # Проверки
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
    assert "Вы не подписаны на этого пользователя" in json_response["error_message"]


async def test_unfollow_user_success(
    authenticated_client: AsyncClient,
    test_user_data: Tuple[User, str],
    test_user_alice_data: Tuple[User, str],
    db_session: AsyncSession,
):
    """Тест успешной отписки."""
    test_user, _ = test_user_data
    test_user_alice, _ = test_user_alice_data

    # Сначала создаем подписку
    follow = Follow(follower_id=test_user.id, following_id=test_user_alice.id)
    db_session.add(follow)
    await db_session.commit()

    # Отписываемся через API
    response = await authenticated_client.delete(
        f"/api/users/{test_user_alice.id}/follow"
    )

    # Проверки
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем, что запись удалена из БД
    follow_rel = await db_session.execute(
        select(Follow).where(
            Follow.follower_id == test_user.id,
            Follow.following_id == test_user_alice.id,
        )
    )

    assert follow_rel.scalar_one_or_none() is None

    # Проверка через API
    response_me = await authenticated_client.get("/api/users/me")
    assert len(response_me.json()["user"]["following"]) == 0
