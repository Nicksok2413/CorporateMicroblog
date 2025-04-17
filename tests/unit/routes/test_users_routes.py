from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.routes.users import (follow_user, get_my_profile,
                                  get_user_profile_by_id, unfollow_user)
from src.schemas.base import ResultTrue
from src.schemas.user import UserProfile, UserProfileResult
from src.services import FollowService, UserService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры для моков зависимостей ---

@pytest.fixture
def mock_user_service() -> MagicMock:
    service = MagicMock(spec=UserService)
    service.get_user_profile = AsyncMock()
    return service


@pytest.fixture
def mock_follow_service() -> MagicMock:
    service = MagicMock(spec=FollowService)
    service.follow_user = AsyncMock()
    service.unfollow_user = AsyncMock()
    return service


# --- Тест для get_my_profile ---

async def test_get_my_profile_handler(
        mock_db_session: MagicMock,
        mock_current_user: MagicMock,
        mock_user_service: MagicMock,
):
    """Юнит-тест для обработчика get_my_profile."""
    # Настраиваем мок сервиса
    expected_profile_data = UserProfile(id=mock_current_user.id, name="Test User", followers=[], following=[])
    mock_user_service.get_user_profile.return_value = expected_profile_data

    # Вызываем обработчик
    result = await get_my_profile(
        db=mock_db_session,
        current_user=mock_current_user,
        user_service=mock_user_service,
    )

    # Проверяем вызов сервиса
    mock_user_service.get_user_profile.assert_awaited_once_with(
        db=mock_db_session, user_id=mock_current_user.id
    )
    # Проверяем результат
    assert isinstance(result, UserProfileResult)
    assert result.user == expected_profile_data


# --- Тест для get_user_profile_by_id ---

async def test_get_user_profile_by_id_handler(
        mock_db_session: MagicMock,
        mock_user_service: MagicMock,
):
    """Юнит-тест для обработчика get_user_profile_by_id."""
    user_id_to_get = 2
    # Настраиваем мок сервиса
    expected_profile_data = UserProfile(id=user_id_to_get, name="Alice", followers=[], following=[])
    mock_user_service.get_user_profile.return_value = expected_profile_data

    # Вызываем обработчик
    result = await get_user_profile_by_id(
        db=mock_db_session,
        user_service=mock_user_service,
        user_id=user_id_to_get,  # Передаем Path параметр напрямую
    )

    # Проверяем вызов сервиса
    mock_user_service.get_user_profile.assert_awaited_once_with(
        db=mock_db_session, user_id=user_id_to_get
    )
    # Проверяем результат
    assert isinstance(result, UserProfileResult)
    assert result.user == expected_profile_data


# --- Тест для follow_user ---

async def test_follow_user_handler(
        mock_db_session: MagicMock,
        mock_current_user: MagicMock,
        mock_follow_service: MagicMock,
):
    """Юнит-тест для обработчика follow_user."""
    user_id_to_follow = 3
    # Настраиваем мок сервиса (метод ничего не возвращает)
    mock_follow_service.follow_user.return_value = None

    # Вызываем обработчик
    result = await follow_user(
        db=mock_db_session,
        current_user=mock_current_user,
        follow_service=mock_follow_service,
        user_id=user_id_to_follow,
    )

    # Проверяем вызов сервиса
    mock_follow_service.follow_user.assert_awaited_once_with(
        db=mock_db_session, current_user=mock_current_user, user_to_follow_id=user_id_to_follow
    )
    # Проверяем результат
    assert isinstance(result, ResultTrue)
    assert result.result is True


# --- Тест для unfollow_user ---

async def test_unfollow_user_handler(
        mock_db_session: MagicMock,
        mock_current_user: MagicMock,
        mock_follow_service: MagicMock,
):
    """Юнит-тест для обработчика unfollow_user."""
    user_id_to_unfollow = 4
    # Настраиваем мок сервиса
    mock_follow_service.unfollow_user.return_value = None

    # Вызываем обработчик
    result = await unfollow_user(
        db=mock_db_session,
        current_user=mock_current_user,
        follow_service=mock_follow_service,
        user_id=user_id_to_unfollow,
    )

    # Проверяем вызов сервиса
    mock_follow_service.unfollow_user.assert_awaited_once_with(
        db=mock_db_session, current_user=mock_current_user, user_to_unfollow_id=user_id_to_unfollow
    )
    # Проверяем результат
    assert isinstance(result, ResultTrue)
    assert result.result is True
