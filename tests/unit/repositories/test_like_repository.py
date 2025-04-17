from unittest.mock import MagicMock

import pytest
from sqlalchemy import delete
from sqlalchemy.engine.result import ScalarResult

from src.models import Like
from src.repositories import LikeRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---
@pytest.fixture
def like_repo() -> LikeRepository:
    """Экземпляр репозитория."""
    return LikeRepository()


# --- Тест для get_like ---

async def test_get_like_found(
        like_repo: LikeRepository,
        mock_db_session: MagicMock,
        test_like_obj: Like
):
    """Тест get_like, когда лайк найден."""
    user_id = 1
    tweet_id = 101

    # Настраиваем мок результата execute
    mock_result = mock_db_session.execute.return_value
    # Мокируем вложенные вызовы scalars().first()
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = test_like_obj  # Возвращаем объект лайка
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Вызываем метод
    result = await like_repo.get_like(
        db=mock_db_session, user_id=user_id, tweet_id=tweet_id
    )

    # Проверяем результат
    assert result == test_like_obj
    # Проверяем, что execute был вызван
    mock_db_session.execute.assert_awaited_once()
    # Проверяем, что scalars() и first() были вызваны
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()


async def test_get_like_not_found(
        like_repo: LikeRepository,
        mock_db_session: MagicMock
):
    """Тест get_like, когда лайк не найден."""
    user_id = 1
    tweet_id = 102

    # Настраиваем мок результата execute
    mock_result = mock_db_session.execute.return_value
    # Мокируем вложенные вызовы scalars().first() для возврата None
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = None  # Лайк не найден
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Вызываем метод
    result = await like_repo.get_like(
        db=mock_db_session, user_id=user_id, tweet_id=tweet_id
    )

    # Проверяем результат
    assert result is None
    # Проверяем вызовы
    mock_db_session.execute.assert_awaited_once()
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()


# --- Тест для add_like ---

async def test_add_like(
        like_repo: LikeRepository,
        mock_db_session: MagicMock
):
    """Тест успешного вызова add_like."""
    user_id = 1
    tweet_id = 103

    # Вызываем метод
    result_like = await like_repo.add_like(
        db=mock_db_session, user_id=user_id, tweet_id=tweet_id
    )

    # Проверяем возвращенный объект
    assert isinstance(result_like, Like)
    assert result_like.user_id == user_id
    assert result_like.tweet_id == tweet_id

    # Проверяем, что session.add был вызван с этим объектом
    mock_db_session.add.assert_called_once_with(result_like)


# --- Тест для delete_like ---

async def test_delete_like(
        like_repo: LikeRepository,
        mock_db_session: MagicMock
):
    """Тест успешного вызова delete_like."""
    user_id = 1
    tweet_id = 104

    # Вызываем метод
    await like_repo.delete_like(
        db=mock_db_session, user_id=user_id, tweet_id=tweet_id
    )

    # Проверяем, что execute был вызван
    mock_db_session.execute.assert_awaited_once()

    # Дополнительно: проверим, что переданный statement - это delete
    # (Это необязательно, но повышает уверенность)
    call_args = mock_db_session.execute.await_args
    assert call_args is not None
    statement = call_args[0][0]  # Первый позиционный аргумент первого вызова
    assert isinstance(statement, type(delete(Like)))  # Проверяем тип statement
