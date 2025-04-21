from unittest.mock import MagicMock

import pytest

from src.api.routes.users import (
    follow_user,
    get_my_profile,
    get_user_profile_by_id,
    unfollow_user,
)
from src.models.user import User
from src.schemas.base import ResultTrue
from src.schemas.user import UserProfile, UserProfileResult

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тест для обработчика роута get_my_profile ---


async def test_get_my_profile_handler(
    mock_db_session: MagicMock,
    test_user_obj: User,
    mock_user_service: MagicMock,
):
    """Юнит-тест для обработчика get_my_profile."""
    # Настраиваем мок сервиса
    expected_profile_data = UserProfile(
        id=test_user_obj.id, name="Test User", followers=[], following=[]
    )
    mock_user_service.get_user_profile.return_value = expected_profile_data

    # Вызываем обработчик
    result = await get_my_profile(
        db=mock_db_session,
        current_user=test_user_obj,
        user_service=mock_user_service,
    )

    # Проверяем вызов сервиса
    mock_user_service.get_user_profile.assert_awaited_once_with(
        db=mock_db_session, user_id=test_user_obj.id
    )

    # Проверяем результат
    assert isinstance(result, UserProfileResult)
    assert result.user == expected_profile_data


# --- Тест для обработчика роута get_user_profile_by_id ---


async def test_get_user_profile_by_id_handler(
    mock_db_session: MagicMock,
    mock_user_service: MagicMock,
):
    """Юнит-тест для обработчика get_user_profile_by_id."""
    user_id_to_get = 2
    # Настраиваем мок сервиса
    expected_profile_data = UserProfile(
        id=user_id_to_get, name="Alice", followers=[], following=[]
    )
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


# --- Тест для обработчика роута follow_user ---


async def test_follow_user_handler(
    mock_db_session: MagicMock,
    test_user_obj: User,
    mock_follow_service: MagicMock,
):
    """Юнит-тест для обработчика follow_user."""
    user_id_to_follow = 3
    # Настраиваем мок сервиса (метод ничего не возвращает)
    mock_follow_service.follow_user.return_value = None

    # Вызываем обработчик
    result = await follow_user(
        db=mock_db_session,
        current_user=test_user_obj,
        follow_service=mock_follow_service,
        user_id=user_id_to_follow,
    )

    # Проверяем вызов сервиса
    mock_follow_service.follow_user.assert_awaited_once_with(
        db=mock_db_session,
        current_user=test_user_obj,
        user_to_follow_id=user_id_to_follow,
    )

    # Проверяем результат
    assert isinstance(result, ResultTrue)
    assert result.result is True


# --- Тест для обработчика роута unfollow_user ---


async def test_unfollow_user_handler(
    mock_db_session: MagicMock,
    test_user_obj: User,
    mock_follow_service: MagicMock,
):
    """Юнит-тест для обработчика unfollow_user."""
    user_id_to_unfollow = 4
    # Настраиваем мок сервиса
    mock_follow_service.unfollow_user.return_value = None

    # Вызываем обработчик
    result = await unfollow_user(
        db=mock_db_session,
        current_user=test_user_obj,
        follow_service=mock_follow_service,
        user_id=user_id_to_unfollow,
    )

    # Проверяем вызов сервиса
    mock_follow_service.unfollow_user.assert_awaited_once_with(
        db=mock_db_session,
        current_user=test_user_obj,
        user_to_unfollow_id=user_id_to_unfollow,
    )

    # Проверяем результат
    assert isinstance(result, ResultTrue)
    assert result.result is True
