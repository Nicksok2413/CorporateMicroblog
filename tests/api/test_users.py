# tests/api/test_users.py
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Follow  # Импортируем модели для type hinting и проверок
from src.schemas.user import UserProfileResult, BaseUser  # Схемы для проверок
from src.schemas.base import ResultTrue

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# === Тесты профилей ===

async def test_get_my_profile_success(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,
        test_user_alice: User,  # Нужна Алиса, чтобы проверить подписки/подписчиков
        db_session: AsyncSession,
):
    """Тест успешного получения своего профиля."""
    # Создадим подписку Alice -> Nick, чтобы проверить список подписчиков
    follow = Follow(follower_id=test_user_alice.id, following_id=test_user_nick.id)
    db_session.add(follow)
    await db_session.commit()

    response = await async_client.get("/api/users/me", headers=nick_headers)

    assert response.status_code == status.HTTP_200_OK
    data = UserProfileResult(**response.json())
    assert data.result is True
    assert data.user.id == test_user_nick.id
    assert data.user.name == test_user_nick.name
    # Проверяем, что Alice есть в подписчиках
    assert len(data.user.followers) == 1
    assert data.user.followers[0].id == test_user_alice.id
    assert data.user.followers[0].name == test_user_alice.name
    # Nick пока ни на кого не подписан в этой фикстуре
    assert len(data.user.following) == 0


async def test_get_my_profile_unauthorized(async_client: AsyncClient):
    """Тест получения своего профиля без авторизации."""
    response = await async_client.get("/api/users/me")  # Без заголовка
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "unauthorized"


async def test_get_user_profile_by_id_success(
        async_client: AsyncClient,
        test_user_alice: User,
        test_user_bob: User,
        db_session: AsyncSession,
        # Не используем заголовки, т.к. эндпоинт доступен без аутентификации
):
    """Тест успешного получения чужого профиля по ID."""
    # Создадим подписку Bob -> Alice, чтобы проверить данные в профиле Alice
    follow = Follow(follower_id=test_user_bob.id, following_id=test_user_alice.id)
    db_session.add(follow)
    await db_session.commit()

    response = await async_client.get(f"/api/users/{test_user_alice.id}")

    assert response.status_code == status.HTTP_200_OK
    data = UserProfileResult(**response.json())
    assert data.result is True
    assert data.user.id == test_user_alice.id
    assert data.user.name == test_user_alice.name
    # Проверяем, что Bob есть в подписчиках
    assert len(data.user.followers) == 1
    assert data.user.followers[0].id == test_user_bob.id
    # Alice пока ни на кого не подписана
    assert len(data.user.following) == 0


async def test_get_user_profile_by_id_not_found(async_client: AsyncClient):
    """Тест получения профиля несуществующего пользователя."""
    response = await async_client.get("/api/users/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


# === Тесты подписок ===

async def test_follow_user_success(
        async_client: AsyncClient,
        nick_headers: dict,  # Nick подписывается
        test_user_nick: User,
        test_user_alice: User,  # На Alice
        db_session: AsyncSession,
):
    """Тест успешной подписки."""
    response = await async_client.post(f"/api/users/{test_user_alice.id}/follow", headers=nick_headers)

    assert response.status_code == status.HTTP_201_CREATED
    data = ResultTrue(**response.json())
    assert data.result is True

    # Проверяем подписку в БД
    follow = await db_session.get(Follow, (test_user_nick.id, test_user_alice.id))
    assert follow is not None


async def test_follow_user_self_forbidden(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,
):
    """Тест попытки подписаться на себя."""
    response = await async_client.post(f"/api/users/{test_user_nick.id}/follow", headers=nick_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"


async def test_follow_user_twice_conflict(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_alice: User,
):
    """Тест повторной подписки."""
    # Первая подписка
    await async_client.post(f"/api/users/{test_user_alice.id}/follow", headers=nick_headers)
    # Вторая подписка
    response = await async_client.post(f"/api/users/{test_user_alice.id}/follow", headers=nick_headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "conflict_error"


async def test_follow_user_not_found(
        async_client: AsyncClient,
        nick_headers: dict,
):
    """Тест подписки на несуществующего пользователя."""
    response = await async_client.post("/api/users/9999/follow", headers=nick_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_unfollow_user_success(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,
        test_user_alice: User,
        db_session: AsyncSession,
):
    """Тест успешной отписки."""
    # Создаем подписку Nick -> Alice
    follow = Follow(follower_id=test_user_nick.id, following_id=test_user_alice.id)
    db_session.add(follow)
    await db_session.commit()

    # Отписываемся через API
    response = await async_client.delete(f"/api/users/{test_user_alice.id}/follow", headers=nick_headers)

    assert response.status_code == status.HTTP_200_OK
    data = ResultTrue(**response.json())
    assert data.result is True

    # Проверяем, что подписка удалена из БД
    deleted_follow = await db_session.get(Follow, (test_user_nick.id, test_user_alice.id))
    assert deleted_follow is None


async def test_unfollow_user_self_forbidden(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,
):
    """Тест попытки отписаться от себя."""
    response = await async_client.delete(f"/api/users/{test_user_nick.id}/follow", headers=nick_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # Запрещено сервисом
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"


async def test_unfollow_user_not_following(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_alice: User,
):
    """Тест отписки от пользователя, на которого не подписан."""
    # Убедимся, что подписки нет (хотя в изолированном тесте ее и так не будет)
    response = await async_client.delete(f"/api/users/{test_user_alice.id}/follow", headers=nick_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"  # Сервис вернет NotFound, если подписки нет


async def test_unfollow_user_target_not_found(
        async_client: AsyncClient,
        nick_headers: dict,
):
    """Тест отписки от несуществующего пользователя."""
    response = await async_client.delete("/api/users/99999/follow", headers=nick_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND  # Сервис вернет NotFound, если целевой юзер не найден
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"
