from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.orm import selectinload

from src.models import Follow
from src.repositories import FollowRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для создания экземпляра репозитория
@pytest.fixture
def follow_repo() -> FollowRepository:
    return FollowRepository()


# --- Тесты для get_follow ---


async def test_get_follow_found(
    follow_repo: FollowRepository,
    mock_db_session: MagicMock,
    test_follow_obj: Follow,
):
    """Тест get_follow, когда подписка найдена."""
    follower_id = 1
    following_id = 2

    # Настраиваем мок результата execute
    mock_result = mock_db_session.execute.return_value
    # Мокируем вложенные вызовы scalars().first()
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = test_follow_obj  # Возвращаем объект подписки
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Вызываем метод
    result = await follow_repo.get_follow(
        db=mock_db_session, follower_id=follower_id, following_id=following_id
    )

    # Проверяем результат
    assert result == test_follow_obj
    # Проверяем, что execute был вызван
    mock_db_session.execute.assert_awaited_once()
    # Проверяем, что scalars() и first() были вызваны
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()


async def test_get_follow_not_found(
    follow_repo: FollowRepository,
    mock_db_session: MagicMock,
):
    """Тест get_follow, когда подписка не найдена."""
    follower_id = 1
    following_id = 3

    # Настраиваем мок результата execute
    mock_result = mock_db_session.execute.return_value
    # Мокируем вложенные вызовы scalars().first() для возврата None
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = None  # Подписка не найдена
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Вызываем метод
    result = await follow_repo.get_follow(
        db=mock_db_session, follower_id=follower_id, following_id=following_id
    )

    # Проверяем результат
    assert result is None
    # Проверяем вызовы
    mock_db_session.execute.assert_awaited_once()
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()


# --- Тесты для add_follow ---
# Покрыт тестами FollowService

# --- Тесты для delete_follow ---


async def test_follow_repo_delete_follow(
    follow_repo: FollowRepository,
    mock_db_session: MagicMock,
):
    """Тест прямого удаления подписки."""
    follower_id = 1
    following_id = 2

    # Настраиваем мок execute
    mock_db_session.execute = AsyncMock()

    # Запускаем метод
    await follow_repo.delete_follow(
        mock_db_session, follower_id=follower_id, following_id=following_id
    )

    # Проверяем, что execute был вызван с правильным delete стейтментом
    assert mock_db_session.execute.await_args[0][0].compare(
        delete(Follow).where(
            Follow.follower_id == follower_id, Follow.following_id == following_id
        )
    )


# --- Тесты для get_following_ids ---


async def test_follow_repo_get_following_ids(
    follow_repo: FollowRepository,
    mock_db_session: MagicMock,
):
    """Тест получения списка ID подписок."""
    follower_id = 1
    expected_ids = [2, 3, 4]

    # Настраиваем мок результата execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = expected_ids
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    ids = await follow_repo.get_following_ids(mock_db_session, follower_id=follower_id)

    assert ids == expected_ids

    # Проверяем вызов execute с правильным select стейтментом
    assert mock_db_session.execute.await_args[0][0].compare(
        select(Follow.following_id).where(Follow.follower_id == follower_id)
    )


# --- Тесты для get_following_with_users ---


async def test_follow_repo_get_following_with_users(
    follow_repo: FollowRepository,
    mock_db_session: MagicMock,
):
    """Тест получения подписок с загрузкой пользователей."""
    follower_id = 1
    mock_follows = [Follow(), Follow()]  # Простые моки для проверки

    # Настраиваем мок результата execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_follows
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    follows = await follow_repo.get_following_with_users(
        mock_db_session, follower_id=follower_id
    )

    assert follows == mock_follows

    # Проверяем вызов execute с правильным select и options
    statement = mock_db_session.execute.await_args[0][0]

    expected_statement = (
        select(Follow)
        .where(Follow.follower_id == follower_id)
        .options(selectinload(Follow.followed_user))
    )

    assert statement.compare(expected_statement)


# --- Тесты для get_followers_with_users ---


async def test_follow_repo_get_followers_with_users(
    follow_repo: FollowRepository,
    mock_db_session: MagicMock,
):
    """Тест получения подписчиков с загрузкой пользователей."""
    following_id = 2
    mock_follows = [Follow(), Follow()]

    # Настраиваем мок результата execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_follows
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    followers = await follow_repo.get_followers_with_users(
        mock_db_session, following_id=following_id
    )

    assert followers == mock_follows

    # Проверяем вызов execute с правильным select и options
    statement = mock_db_session.execute.await_args[0][0]

    expected_statement = (
        select(Follow)
        .where(Follow.following_id == following_id)
        .options(selectinload(Follow.follower))
    )

    assert statement.compare(expected_statement)
