from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError  # Для имитации ошибок БД

from src.core.exceptions import BadRequestError, NotFoundError
from src.models import Like, Tweet, User
from src.services.like_service import LikeService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---

# Фикстура для создания экземпляра сервиса
@pytest.fixture
def like_service(
        mock_like_repo: MagicMock,
        mock_tweet_repo: MagicMock
) -> LikeService:
    service = LikeService(repo=mock_like_repo, tweet_repo=mock_tweet_repo)
    return service


# --- Тесты для like_tweet ---

async def test_like_tweet_success(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        mock_tweet_repo: MagicMock,
        mock_like_repo: MagicMock,
):
    """Тест успешного лайка."""
    # Настраиваем моки
    mock_tweet_repo.get.return_value = test_tweet_obj
    mock_like_repo.add_like.return_value = Like(user_id=test_user_obj.id, tweet_id=test_tweet_obj.id)

    # Вызываем метод сервиса
    await like_service.like_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=test_tweet_obj.id)

    # Проверяем вызовы
    mock_tweet_repo.get.assert_awaited_once_with(mock_db_session, obj_id=test_tweet_obj.id)
    mock_like_repo.add_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                     tweet_id=test_tweet_obj.id)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_like_tweet_tweet_not_found(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
        mock_like_repo: MagicMock,
):
    """Тест лайка несуществующего твита."""
    tweet_id = 999
    # Настраиваем мок tweet_repo.get на возврат None
    mock_tweet_repo.get.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await like_service.like_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_tweet_repo.get.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    # Проверяем, что другие методы не вызывались
    mock_like_repo.add_like.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_not_awaited()


async def test_like_tweet_db_error(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        mock_tweet_repo: MagicMock,
        mock_like_repo: MagicMock,
):
    """Тест ошибки БД при добавлении лайка."""
    # Настраиваем моки
    mock_tweet_repo.get.return_value = test_tweet_obj
    # Имитируем ошибку при вызове add_like
    mock_like_repo.add_like.side_effect = SQLAlchemyError("DB error")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await like_service.like_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=test_tweet_obj.id)

    # Проверяем вызовы
    mock_tweet_repo.get.assert_awaited_once()
    mock_like_repo.add_like.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


# --- Тесты для unlike_tweet ---

async def test_unlike_tweet_success(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        test_like_obj: Like,
        mock_like_repo: MagicMock,
):
    """Тест успешного удаления лайка."""
    tweet_id = test_tweet_obj.id
    # Настраиваем мок
    # Имитируем, что лайк существует
    mock_like_repo.get_like.return_value = test_like_obj
    mock_like_repo.delete_like.return_value = None  # Метод ничего не возвращает

    # Вызываем метод сервиса
    await like_service.unlike_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_like_repo.get_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                     tweet_id=tweet_id)
    mock_like_repo.delete_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                        tweet_id=tweet_id)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_unlike_tweet_like_not_found(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        mock_like_repo: MagicMock,
):
    """Тест удаления несуществующего лайка."""
    tweet_id = test_tweet_obj.id
    # Настраиваем мок
    # Имитируем, что лайк не существует
    mock_like_repo.get_like.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await like_service.unlike_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_like_repo.get_like.assert_awaited_once_with(mock_db_session, user_id=test_user_obj.id,
                                                     tweet_id=tweet_id)
    # Проверяем, что другие методы не вызывались
    mock_like_repo.delete_like.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_not_awaited()


async def test_unlike_tweet_db_error(
        like_service: LikeService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        test_like_obj: Like,
        mock_like_repo: MagicMock,
):
    """Тест ошибки БД при удалении лайка."""
    tweet_id = test_tweet_obj.id
    # Настраиваем мок
    mock_like_repo.get_like.return_value = test_like_obj
    # Имитируем ошибку при вызове delete_like
    mock_like_repo.delete_like.side_effect = SQLAlchemyError("DB error on delete")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await like_service.unlike_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_like_repo.get_like.assert_awaited_once()
    mock_like_repo.delete_like.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк
