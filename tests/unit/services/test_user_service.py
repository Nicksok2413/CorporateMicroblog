from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import NotFoundError
from src.models import User, Follow
from src.repositories import UserRepository, FollowRepository
from src.schemas.user import BaseUser, UserProfile
from src.services.user_service import UserService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для моков репозиториев
@pytest.fixture
def mock_user_repo() -> MagicMock:
    repo = MagicMock(spec=UserRepository)
    repo.get_by_api_key = AsyncMock()
    repo.get = AsyncMock()  # Для _get_obj_or_404
    # Имя модели для сообщений об ошибках
    repo.model = User
    return repo


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
    """Тест успешного поиска пользователя по ключу."""
    api_key = "test_key"
    user_service._mock_user_repo.get_by_api_key.return_value = test_user_obj

    user = await user_service.get_user_by_api_key(db=mock_db_session, api_key=api_key)

    assert user == test_user_obj
    user_service._mock_user_repo.get_by_api_key.assert_awaited_once_with(db=mock_db_session, api_key=api_key)


async def test_get_user_by_api_key_not_found(
        user_service: UserService,
        mock_db_session: MagicMock,
):
    """Тест случая, когда пользователь по ключу не найден."""
    api_key = "not_found_key"
    user_service._mock_user_repo.get_by_api_key.return_value = None

    user = await user_service.get_user_by_api_key(db=mock_db_session, api_key=api_key)

    assert user is None
    user_service._mock_user_repo.get_by_api_key.assert_awaited_once_with(db=mock_db_session, api_key=api_key)


# --- Тесты для get_user_profile ---

async def test_get_user_profile_success(
        user_service: UserService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        test_bob_obj: User,
):
    """Тест успешного получения профиля пользователя с подписками/подписчиками."""
    user_id_to_get = test_user_obj.id
    user_service._mock_user_repo.get.return_value = test_user_obj  # Пользователь найден

    # Мокируем данные от follow_repo
    # Допустим, Alice подписана на User, а User подписан на Bob
    follower_relation = MagicMock(spec=Follow)
    follower_relation.follower = test_alice_obj  # Alice подписчик
    following_relation = MagicMock(spec=Follow)
    following_relation.followed_user = test_bob_obj  # User подписан на Bob

    user_service._mock_follow_repo.get_followers_with_users.return_value = [follower_relation]
    user_service._mock_follow_repo.get_following_with_users.return_value = [following_relation]

    # Вызываем метод
    profile: UserProfile = await user_service.get_user_profile(db=mock_db_session, user_id=user_id_to_get)

    # Проверяем результат
    assert isinstance(profile, UserProfile)
    assert profile.id == test_user_obj.id
    assert profile.name == test_user_obj.name

    # Проверяем подписчиков
    assert len(profile.followers) == 1
    assert isinstance(profile.followers[0], BaseUser)
    assert profile.followers[0].id == test_alice_obj.id
    assert profile.followers[0].name == test_alice_obj.name

    # Проверяем подписки
    assert len(profile.following) == 1
    assert isinstance(profile.following[0], BaseUser)
    assert profile.following[0].id == test_bob_obj.id
    assert profile.following[0].name == test_bob_obj.name

    # Проверяем вызовы моков
    user_service._mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id_to_get)
    user_service._mock_follow_repo.get_followers_with_users.assert_awaited_once_with(db=mock_db_session,
                                                                                     following_id=user_id_to_get)
    user_service._mock_follow_repo.get_following_with_users.assert_awaited_once_with(db=mock_db_session,
                                                                                     follower_id=user_id_to_get)


async def test_get_user_profile_user_not_found(
        user_service: UserService,
        mock_db_session: MagicMock,
):
    """Тест получения профиля несуществующего пользователя."""
    user_id_to_get = 999
    # Имитируем, что user_repo.get вернет None
    user_service._mock_user_repo.get.return_value = None

    # Проверяем исключение
    with pytest.raises(NotFoundError) as exc_info:
        await user_service.get_user_profile(db=mock_db_session, user_id=user_id_to_get)

    assert f"User с ID {user_id_to_get} не найден" in str(exc_info.value)
    user_service._mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=user_id_to_get)
    # Методы follow_repo не должны были вызваться
    user_service._mock_follow_repo.get_followers_with_users.assert_not_awaited()
    user_service._mock_follow_repo.get_following_with_users.assert_not_awaited()
