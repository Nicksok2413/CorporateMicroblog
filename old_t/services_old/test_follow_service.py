"""Юнит-тесты для FollowService."""

import pytest
from unittest.mock import AsyncMock

from app.services.follow_service import follow_service
from app.models import User, Follow
from app.core.exceptions import PermissionDeniedError, NotFoundError, ConflictError


@pytest.mark.asyncio
async def test_follow_user_service_success(mocker):
    """Тест успешной подписки."""
    mock_user_repo = mocker.patch("src.services_old.follow_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.follow_service.follow_repo", autospec=True)

    # Данные
    current_user = User(id=1)
    user_to_follow = User(id=2)

    # Настройка моков
    mock_user_repo.get.return_value = user_to_follow  # Целевой пользователь существует
    mock_follow_repo.get_follow.return_value = None  # Подписки еще нет
    mock_follow_repo.add_follow.return_value = Follow(follower_id=1, following_id=2)

    db_session_mock = AsyncMock()

    # Вызов - не должно быть исключений
    await follow_service.follow_user(db=db_session_mock, current_user=current_user, user_to_follow_id=2)

    # Проверки
    mock_user_repo.get.assert_called_once_with(db_session_mock, id=2)
    mock_follow_repo.get_follow.assert_called_once_with(db=db_session_mock, follower_id=1, following_id=2)
    mock_follow_repo.add_follow.assert_called_once_with(db=db_session_mock, follower_id=1, following_id=2)


@pytest.mark.asyncio
async def test_follow_user_service_self(mocker):
    """Тест подписки на себя."""
    mock_user_repo = mocker.patch("src.services_old.follow_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.follow_service.follow_repo", autospec=True)

    current_user = User(id=1)
    db_session_mock = AsyncMock()

    with pytest.raises(PermissionDeniedError):
        await follow_service.follow_user(db=db_session_mock, current_user=current_user, user_to_follow_id=1)

    mock_user_repo.get.assert_not_called()
    mock_follow_repo.get_follow.assert_not_called()
    mock_follow_repo.add_follow.assert_not_called()


@pytest.mark.asyncio
async def test_follow_user_service_target_not_found(mocker):
    """Тест подписки на несуществующего пользователя."""
    mock_user_repo = mocker.patch("src.services_old.follow_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.follow_service.follow_repo", autospec=True)

    current_user = User(id=1)
    mock_user_repo.get.return_value = None  # Целевой пользователь не найден

    db_session_mock = AsyncMock()

    with pytest.raises(NotFoundError):
        await follow_service.follow_user(db=db_session_mock, current_user=current_user, user_to_follow_id=99)

    mock_follow_repo.get_follow.assert_not_called()
    mock_follow_repo.add_follow.assert_not_called()


@pytest.mark.asyncio
async def test_follow_user_service_already_following(mocker):
    """Тест повторной подписки."""
    mock_user_repo = mocker.patch("src.services_old.follow_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.follow_service.follow_repo", autospec=True)

    current_user = User(id=1)
    user_to_follow = User(id=2)
    mock_user_repo.get.return_value = user_to_follow
    mock_follow_repo.get_follow.return_value = Follow(follower_id=1, following_id=2)  # Подписка уже есть

    db_session_mock = AsyncMock()

    with pytest.raises(ConflictError):
        await follow_service.follow_user(db=db_session_mock, current_user=current_user, user_to_follow_id=2)

    mock_follow_repo.add_follow.assert_not_called()


# --- Тесты для unfollow_user ---

@pytest.mark.asyncio
async def test_unfollow_user_service_success(mocker):
    """Тест успешной отписки."""
    mock_user_repo = mocker.patch("src.services_old.follow_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.follow_service.follow_repo", autospec=True)

    current_user = User(id=1)
    user_to_unfollow = User(id=2)
    mock_user_repo.get.return_value = user_to_unfollow
    mock_follow_repo.delete_follow.return_value = True  # Подписка найдена и удалена

    db_session_mock = AsyncMock()

    await follow_service.unfollow_user(db=db_session_mock, current_user=current_user, user_to_unfollow_id=2)

    mock_user_repo.get.assert_called_once_with(db_session_mock, id=2)
    mock_follow_repo.delete_follow.assert_called_once_with(db=db_session_mock, follower_id=1, following_id=2)


@pytest.mark.asyncio
async def test_unfollow_user_service_not_following(mocker):
    """Тест отписки, если не был подписан."""
    mock_user_repo = mocker.patch("src.services_old.follow_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.follow_service.follow_repo", autospec=True)

    current_user = User(id=1)
    user_to_unfollow = User(id=2)
    mock_user_repo.get.return_value = user_to_unfollow
    mock_follow_repo.delete_follow.return_value = False  # Подписка не найдена

    db_session_mock = AsyncMock()

    with pytest.raises(NotFoundError):
        await follow_service.unfollow_user(db=db_session_mock, current_user=current_user, user_to_unfollow_id=2)

    mock_follow_repo.delete_follow.assert_called_once_with(db=db_session_mock, follower_id=1, following_id=2)

# TODO: Добавить тесты для _validate_follow_action (хотя они косвенно покрываются другими тестами)
