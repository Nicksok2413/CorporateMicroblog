from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError  # Для имитации ошибок БД

from src.core.exceptions import NotFoundError, BadRequestError
from src.models import Tweet, User, Like
from src.services.like_service import LikeService
from src.repositories import LikeRepository, TweetRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---
# Фикстура для мока LikeRepository
@pytest.fixture
def mock_like_repo() -> MagicMock:
    repo = MagicMock(spec=LikeRepository)
    repo.get_like = AsyncMock()
    repo.add_like = AsyncMock()
    repo.delete_like = AsyncMock()
    return repo


# Фикстура для мока TweetRepository
@pytest.fixture
def mock_tweet_repo() -> MagicMock:
    repo = MagicMock(spec=TweetRepository)
    repo.get = AsyncMock()
    return repo


# Фикстура для создания экземпляра сервиса
@pytest.fixture
def like_service(
        mock_like_repo: MagicMock,
        mock_tweet_repo: MagicMock
) -> LikeService:
    service = LikeService(repo=mock_like_repo, tweet_repo=mock_tweet_repo)
    # Сохраняем моки для доступа в тестах
    service._mock_like_repo = mock_like_repo
    service._mock_tweet_repo = mock_tweet_repo
    return service


# --- Тесты для like_tweet ---

async def test_like_tweet_success(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
):
    """Тест успешного лайка."""
    # Настраиваем моки
    like_service._mock_tweet_repo.get.return_value = test_tweet_obj
    like_service._mock_like_repo.add_like.return_value = Like(user_id=test_user_obj.id, tweet_id=test_tweet_obj.id)

    # Вызываем метод сервиса
    await like_service.like_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=test_tweet_obj.id)

    # Проверяем вызовы
    like_service._mock_tweet_repo.get.assert_awaited_once_with(mock_db_session, obj_id=test_tweet_obj.id)
    like_service._mock_like_repo.add_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                                   tweet_id=test_tweet_obj.id)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_like_tweet_tweet_not_found(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
):
    """Тест лайка несуществующего твита."""
    tweet_id = 999
    # Настраиваем мок tweet_repo.get на возврат None
    like_service._mock_tweet_repo.get.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await like_service.like_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    like_service._mock_tweet_repo.get.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    # Проверяем, что другие методы не вызывались
    like_service._mock_like_repo.add_like.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_not_awaited()


async def test_like_tweet_db_error(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
):
    """Тест ошибки БД при добавлении лайка."""
    # Настраиваем моки
    like_service._mock_tweet_repo.get.return_value = test_tweet_obj
    # Имитируем ошибку при вызове add_like
    like_service._mock_like_repo.add_like.side_effect = SQLAlchemyError("DB error")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await like_service.like_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=test_tweet_obj.id)

    # Проверяем вызовы
    like_service._mock_tweet_repo.get.assert_awaited_once()
    like_service._mock_like_repo.add_like.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


# --- Тесты для unlike_tweet ---

async def test_unlike_tweet_success(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        test_like_obj: Like,
):
    """Тест успешного удаления лайка."""
    tweet_id = test_tweet_obj.id
    # Настраиваем мок
    # Имитируем, что лайк существует
    like_service._mock_like_repo.get_like.return_value = test_like_obj
    like_service._mock_like_repo.delete_like.return_value = None  # Метод ничего не возвращает

    # Вызываем метод сервиса
    await like_service.unlike_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    like_service._mock_like_repo.get_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                                   tweet_id=tweet_id)
    like_service._mock_like_repo.delete_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                                      tweet_id=tweet_id)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_unlike_tweet_like_not_found(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
):
    """Тест удаления несуществующего лайка."""
    tweet_id = test_tweet_obj.id
    # Настраиваем мок
    # Имитируем, что лайк не существует
    like_service._mock_like_repo.get_like.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await like_service.unlike_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    like_service._mock_like_repo.get_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                                   tweet_id=tweet_id)
    # Проверяем, что другие методы не вызывались
    like_service._mock_like_repo.delete_like.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_not_awaited()


async def test_unlike_tweet_db_error(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        test_like_obj: Like,
):
    """Тест ошибки БД при удалении лайка."""
    tweet_id = test_tweet_obj.id
    # Настраиваем мок
    like_service._mock_like_repo.get_like.return_value = test_like_obj
    # Имитируем ошибку при вызове delete_like
    like_service._mock_like_repo.delete_like.side_effect = SQLAlchemyError("DB error on delete")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await like_service.unlike_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    like_service._mock_like_repo.get_like.assert_awaited_once()
    like_service._mock_like_repo.delete_like.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк
