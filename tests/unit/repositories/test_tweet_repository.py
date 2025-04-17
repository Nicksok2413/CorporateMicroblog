from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from src.models import Like, Tweet
from src.repositories import TweetRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для репозитория
@pytest.fixture
def tweet_repo() -> TweetRepository:
    return TweetRepository(Tweet)


# --- Тесты для get_with_attachments ---

async def test_tweet_repo_get_with_attachments(tweet_repo, mock_db_session):
    """Тест получения твита с загрузкой медиа."""
    tweet_id = 1
    expected_tweet_obj = Tweet(id=tweet_id)

    mock_result = MagicMock()
    # Настраиваем цепочку вызовов: scalars().first() вернет наш объект
    mock_result.scalars.return_value.first.return_value = expected_tweet_obj
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    actual_tweet = await tweet_repo.get_with_attachments(mock_db_session, tweet_id=tweet_id)

    # Сравниваем actual_tweet с expected_tweet_obj
    assert actual_tweet == expected_tweet_obj

    # Проверяем, что метод scalars() был вызван на результате execute
    mock_result.scalars.assert_called_once()
    # Проверяем, что метод first() был вызван на результате scalars()
    mock_result.scalars.return_value.first.assert_called_once()

    # Проверка вызова execute и сравнение statement
    statement = mock_db_session.execute.await_args[0][0]

    expected_statement = (
        select(Tweet)
        .where(Tweet.id == tweet_id)
        .options(
            selectinload(Tweet.attachments)
        )
    )

    assert statement.compare(expected_statement)


# --- Тесты для get_feed_for_user ---

async def test_tweet_repo_get_feed_for_user(tweet_repo, mock_db_session):
    """Тест получения ленты твитов."""
    author_ids = [1, 2]
    mock_tweets = [Tweet(id=10), Tweet(id=11)]

    # Настраиваем мок результата execute
    mock_result = MagicMock()
    mock_result.unique.return_value.scalars.return_value.all.return_value = mock_tweets
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    tweets = await tweet_repo.get_feed_for_user(mock_db_session, author_ids=author_ids)

    assert tweets == mock_tweets

    # Получаем statement, который был реально выполнен
    statement = mock_db_session.execute.await_args[0][0]

    # Конструируем ожидаемый statement, включая все опции и сортировку
    like_count_subquery = (
        select(Like.tweet_id, func.count(Like.user_id).label("like_count"))
        .group_by(Like.tweet_id)
        .subquery()
    )
    expected_statement = (
        select(Tweet)
        .where(Tweet.author_id.in_(author_ids))  # Используем in_()
        .outerjoin(like_count_subquery, Tweet.id == like_count_subquery.c.tweet_id)
        .options(
            selectinload(Tweet.author),
            selectinload(Tweet.likes).selectinload(Like.user),  # Точно как в репо
            selectinload(Tweet.attachments)
        )
        .order_by(
            desc(like_count_subquery.c.like_count).nulls_last(),
            desc(Tweet.id)
        )
    )

    # Сравниваем сгенерированные стейтменты
    assert statement.compare(expected_statement)


async def test_tweet_repo_get_feed_for_user_empty_authors(tweet_repo, mock_db_session):
    """Тест получения ленты с пустым списком авторов."""
    result = await tweet_repo.get_feed_for_user(mock_db_session, author_ids=[])
    assert result == []
    mock_db_session.execute.assert_not_awaited()  # Не должно быть запроса к БД
