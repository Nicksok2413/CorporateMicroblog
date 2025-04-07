"""Юнит-тесты для UserService."""

import pytest
from unittest.mock import AsyncMock

from app.services.user_service import user_service
from app.models import User, Follow
from app.schemas.user import UserProfile
from app.core.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_get_user_profile_service_success(mocker):
    """Тест успешного получения профиля пользователя."""
    # Моки репозиториев
    mock_user_repo = mocker.patch("src.services_old.user_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.user_service.follow_repo", autospec=True)

    # Данные
    target_user_id = 1
    target_user = User(id=target_user_id, name="Alice")
    follower_user = User(id=2, name="Bob")
    following_user = User(id=3, name="Charlie")

    # Настройка моков
    mock_user_repo.get.return_value = target_user
    # Мок для get_following_with_users (на кого подписана Alice)
    mock_follow_repo.get_following_with_users.return_value = [
        Follow(follower_id=target_user_id, following_id=following_user.id, followed_user=following_user)
    ]
    # Мок для get_followers_with_users (кто подписан на Alice)
    mock_follow_repo.get_followers_with_users.return_value = [
        Follow(follower_id=follower_user.id, following_id=target_user_id, follower=follower_user)
    ]

    db_session_mock = AsyncMock()

    # Вызов сервиса
    profile: UserProfile = await user_service.get_user_profile(db=db_session_mock, user_id=target_user_id)

    # Проверки
    assert profile is not None
    assert profile.id == target_user_id
    assert profile.name == "Alice"

    # Проверка списка подписок (following)
    assert len(profile.following) == 1
    assert profile.following[0].id == following_user.id
    assert profile.following[0].name == "Charlie"

    # Проверка списка подписчиков (followers)
    assert len(profile.followers) == 1
    assert profile.followers[0].id == follower_user.id
    assert profile.followers[0].name == "Bob"

    # Проверка вызовов репозиториев
    mock_user_repo.get.assert_called_once_with(db_session_mock, target_user_id)
    mock_follow_repo.get_following_with_users.assert_called_once_with(db=db_session_mock, follower_id=target_user_id)
    mock_follow_repo.get_followers_with_users.assert_called_once_with(db=db_session_mock, following_id=target_user_id)


@pytest.mark.asyncio
async def test_get_user_profile_service_not_found(mocker):
    """Тест получения профиля несуществующего пользователя."""
    mock_user_repo = mocker.patch("src.services_old.user_service.user_repo", autospec=True)
    mock_follow_repo = mocker.patch("src.services_old.user_service.follow_repo", autospec=True)

    mock_user_repo.get.return_value = None  # Пользователь не найден

    db_session_mock = AsyncMock()

    with pytest.raises(NotFoundError):
        await user_service.get_user_profile(db=db_session_mock, user_id=99)

    # Убедимся, что репозитории подписок не вызывались
    mock_follow_repo.get_following_with_users.assert_not_called()
    mock_follow_repo.get_followers_with_users.assert_not_called()
