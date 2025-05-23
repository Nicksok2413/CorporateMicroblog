from unittest.mock import MagicMock

import pytest

from src.core.exceptions import NotFoundError
from src.models import Follow, User
from src.schemas.user import BaseUser, UserProfile
from src.services.user_service import UserService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для создания экземпляра сервиса
@pytest.fixture
def user_service(mock_user_repo: MagicMock, mock_follow_repo: MagicMock) -> UserService:
    service = UserService(repo=mock_user_repo, follow_repo=mock_follow_repo)
    return service


# --- Тесты для get_user_profile ---


async def test_get_user_profile_success(
    user_service: UserService,
    mock_db_session: MagicMock,
    test_user_obj: User,  # Пользователь, чей профиль запрашиваем
    test_alice_obj: User,  # Подписчик
    test_bob_obj: User,  # На кого подписан
    mock_user_repo: MagicMock,
    mock_follow_repo: MagicMock,
):
    """Тест успешного получения профиля со списками подписчиков и подписок."""
    user_id = test_user_obj.id

    # Мокируем объекты Follow с реальными вложенными пользователями
    mock_follower_rel = Follow(follower_id=test_alice_obj.id, following_id=user_id)
    mock_follower_rel.follower = test_alice_obj

    mock_following_rel = Follow(follower_id=user_id, following_id=test_bob_obj.id)
    mock_following_rel.followed_user = test_bob_obj

    # Настраиваем моки
    mock_user_repo.get.return_value = test_user_obj
    mock_follow_repo.get_following_with_users.return_value = [mock_following_rel]
    mock_follow_repo.get_followers_with_users.return_value = [mock_follower_rel]

    # Вызываем метод
    profile = await user_service.get_user_profile(db=mock_db_session, user_id=user_id)

    # Проверки
    assert isinstance(profile, UserProfile)
    assert profile.id == test_user_obj.id
    assert profile.name == test_user_obj.name

    # Проверяем followers
    assert len(profile.followers) == 1
    assert isinstance(profile.followers[0], BaseUser)
    assert profile.followers[0].id == test_alice_obj.id
    assert profile.followers[0].name == test_alice_obj.name

    # Проверяем following
    assert len(profile.following) == 1
    assert isinstance(profile.following[0], BaseUser)
    assert profile.following[0].id == test_bob_obj.id
    assert profile.following[0].name == test_bob_obj.name

    # Проверяем вызовы моков
    mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id)
    mock_follow_repo.get_following_with_users.assert_awaited_once_with(
        mock_db_session, follower_id=user_id
    )
    mock_follow_repo.get_followers_with_users.assert_awaited_once_with(
        mock_db_session, following_id=user_id
    )


async def test_get_user_profile_success_no_follows(
    user_service: UserService,
    mock_db_session: MagicMock,
    test_user_obj: User,
    mock_user_repo: MagicMock,
    mock_follow_repo: MagicMock,
):
    """Тест успешного получения профиля без подписчиков и подписок."""
    user_id = test_user_obj.id

    # Настраиваем моки
    mock_user_repo.get.return_value = test_user_obj
    mock_follow_repo.get_following_with_users.return_value = []  # Пустой список
    mock_follow_repo.get_followers_with_users.return_value = []  # Пустой список

    # Вызываем метод
    profile = await user_service.get_user_profile(db=mock_db_session, user_id=user_id)

    # Проверки
    assert isinstance(profile, UserProfile)
    assert profile.id == test_user_obj.id
    assert profile.name == test_user_obj.name
    assert profile.followers == []
    assert profile.following == []

    # Проверяем вызовы моков
    mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id)
    mock_follow_repo.get_following_with_users.assert_awaited_once_with(
        mock_db_session, follower_id=user_id
    )
    mock_follow_repo.get_followers_with_users.assert_awaited_once_with(
        mock_db_session, following_id=user_id
    )


async def test_get_user_profile_not_found(
    user_service: UserService,
    mock_db_session: MagicMock,
    mock_user_repo: MagicMock,
    mock_follow_repo: MagicMock,
):
    """Тест получения профиля несуществующего пользователя."""
    user_id = 999
    # Настраиваем мок
    mock_user_repo.get.return_value = None  # Пользователь не найден

    # Проверяем, что выбрасывается NotFoundError (из _get_obj_or_404)
    with pytest.raises(NotFoundError) as exc_info:
        await user_service.get_user_profile(db=mock_db_session, user_id=user_id)

    # Проверяем сообщение об ошибке
    assert f"User с ID {user_id} не найден" in str(exc_info.value)

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id)
    # Методы follow_repo не должны были вызываться
    mock_follow_repo.get_following_with_users.assert_not_awaited()
    mock_follow_repo.get_followers_with_users.assert_not_awaited()
