from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import NotFoundError
from src.models import Follow, User
from src.repositories import FollowRepository, UserRepository
from src.schemas.user import BaseUser, UserProfile
from src.services.user_service import UserService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---
# Фикстура для мока UserRepository
@pytest.fixture
def mock_user_repo() -> MagicMock:
    repo = MagicMock(spec=UserRepository)
    repo.get_by_api_key = AsyncMock()
    repo.get = AsyncMock()
    repo.model = User
    return repo


# Фикстура для мока FollowRepository
@pytest.fixture
def mock_follow_repo() -> MagicMock:
    repo = MagicMock(spec=FollowRepository)
    repo.get_following_with_users = AsyncMock()
    repo.get_followers_with_users = AsyncMock()
    return repo


# Фикстура для создания экземпляра сервиса
@pytest.fixture
def user_service(
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock
) -> UserService:
    service = UserService(repo=mock_user_repo, follow_repo=mock_follow_repo)
    # Сохраняем моки для доступа в тестах
    service._mock_user_repo = mock_user_repo
    service._mock_follow_repo = mock_follow_repo
    return service


# --- Тесты для get_user_by_api_key ---

async def test_get_user_by_api_key_found(
        user_service: UserService,
        mock_db_session: MagicMock,
        test_user_obj: User
):
    """Тест успешного нахождения пользователя по API ключу."""
    api_key = test_user_obj.api_key
    # Настраиваем мок
    user_service._mock_user_repo.get_by_api_key.return_value = test_user_obj

    # Вызываем метод
    found_user = await user_service.get_user_by_api_key(db=mock_db_session, api_key=api_key)

    # Проверки
    assert found_user == test_user_obj
    user_service._mock_user_repo.get_by_api_key.assert_awaited_once_with(mock_db_session, api_key=api_key)


async def test_get_user_by_api_key_not_found(
        user_service: UserService,
        mock_db_session: MagicMock,
):
    """Тест случая, когда пользователь по ключу не найден."""
    api_key = "not_found_key"
    # Настраиваем мок
    user_service._mock_user_repo.get_by_api_key.return_value = None

    # Вызываем метод
    found_user = await user_service.get_user_by_api_key(db=mock_db_session, api_key=api_key)

    # Проверки
    assert found_user is None
    user_service._mock_user_repo.get_by_api_key.assert_awaited_once_with(mock_db_session, api_key=api_key)


# --- Тесты для get_user_profile ---

async def test_get_user_profile_success(
        user_service: UserService,
        mock_db_session: MagicMock,
        test_user_obj: User,  # Пользователь, чей профиль запрашиваем
        test_alice_obj: User,  # Подписчик
        test_bob_obj: User,  # На кого подписан
):
    """Тест успешного получения профиля со списками подписчиков и подписок."""
    user_id = test_user_obj.id

    # Мокируем объекты Follow с реальными вложенными пользователями
    mock_follower_rel = Follow(follower_id=test_alice_obj.id, following_id=user_id)
    mock_follower_rel.follower = test_alice_obj

    mock_following_rel = Follow(follower_id=user_id, following_id=test_bob_obj.id)
    mock_following_rel.followed_user = test_bob_obj

    # Настраиваем моки
    user_service._mock_user_repo.get.return_value = test_user_obj
    user_service._mock_follow_repo.get_following_with_users.return_value = [mock_following_rel]
    user_service._mock_follow_repo.get_followers_with_users.return_value = [mock_follower_rel]

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
    user_service._mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id)
    user_service._mock_follow_repo.get_following_with_users.assert_awaited_once_with(mock_db_session,
                                                                                     follower_id=user_id)
    user_service._mock_follow_repo.get_followers_with_users.assert_awaited_once_with(mock_db_session,
                                                                                     following_id=user_id)


async def test_get_user_profile_success_no_follows(
        user_service: UserService,
        mock_db_session: MagicMock,
        test_user_obj: User,
):
    """Тест успешного получения профиля без подписчиков и подписок."""
    user_id = test_user_obj.id

    # Настраиваем моки
    user_service._mock_user_repo.get.return_value = test_user_obj
    user_service._mock_follow_repo.get_following_with_users.return_value = []  # Пустой список
    user_service._mock_follow_repo.get_followers_with_users.return_value = []  # Пустой список

    # Вызываем метод
    profile = await user_service.get_user_profile(db=mock_db_session, user_id=user_id)

    # Проверки
    assert isinstance(profile, UserProfile)
    assert profile.id == test_user_obj.id
    assert profile.name == test_user_obj.name
    assert profile.followers == []
    assert profile.following == []

    # Проверяем вызовы моков
    user_service._mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id)
    user_service._mock_follow_repo.get_following_with_users.assert_awaited_once_with(mock_db_session,
                                                                                     follower_id=user_id)
    user_service._mock_follow_repo.get_followers_with_users.assert_awaited_once_with(mock_db_session,
                                                                                     following_id=user_id)


async def test_get_user_profile_not_found(
        user_service: UserService,
        mock_db_session: MagicMock,
):
    """Тест получения профиля несуществующего пользователя."""
    user_id = 999
    # Настраиваем мок
    user_service._mock_user_repo.get.return_value = None  # Пользователь не найден

    # Проверяем, что выбрасывается NotFoundError (из _get_obj_or_404)
    with pytest.raises(NotFoundError) as exc_info:
        await user_service.get_user_profile(db=mock_db_session, user_id=user_id)

    assert f"User с ID {user_id} не найден" in str(exc_info.value)

    # Проверяем вызовы
    user_service._mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id)
    # Методы follow_repo не должны были вызываться
    user_service._mock_follow_repo.get_following_with_users.assert_not_awaited()
    user_service._mock_follow_repo.get_followers_with_users.assert_not_awaited()
