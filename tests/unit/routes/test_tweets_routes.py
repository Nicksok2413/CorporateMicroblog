from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.routes.tweets import (create_tweet, delete_tweet,
                                   get_tweets_feed, like_tweet, unlike_tweet)
from src.models import Tweet, User
from src.schemas.tweet import (TweetActionResult, TweetCreateRequest,
                               TweetCreateResult, TweetFeedResult)
from src.services import LikeService, TweetService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры для моков зависимостей ---

@pytest.fixture
def mock_tweet_service() -> MagicMock:
    service = MagicMock(spec=TweetService)
    service.get_tweet_feed = AsyncMock()
    service.create_tweet = AsyncMock()
    service.delete_tweet = AsyncMock()
    return service


@pytest.fixture
def mock_like_service() -> MagicMock:
    service = MagicMock(spec=LikeService)
    service.like_tweet = AsyncMock()
    service.unlike_tweet = AsyncMock()
    return service


# --- Тест для get_tweets_feed ---

async def test_get_tweets_feed_handler(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_service: MagicMock,
):
    """Юнит-тест для обработчика get_tweets_feed."""
    # Настраиваем мок сервиса
    expected_feed = TweetFeedResult(tweets=[])  # Пример результата
    mock_tweet_service.get_tweet_feed.return_value = expected_feed

    # Вызываем обработчик
    result = await get_tweets_feed(
        db=mock_db_session,
        current_user=test_user_obj,
        tweet_service=mock_tweet_service,
    )

    # Проверяем вызов сервиса
    mock_tweet_service.get_tweet_feed.assert_awaited_once_with(
        db=mock_db_session, current_user=test_user_obj
    )
    # Проверяем результат
    assert result == expected_feed


# --- Тест для create_tweet ---

async def test_create_tweet_handler(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_service: MagicMock,
):
    """Юнит-тест для обработчика create_tweet."""
    # Входные данные
    tweet_in_data = TweetCreateRequest(tweet_data="Test content", tweet_media_ids=[])
    # Настраиваем мок сервиса
    tweet_id = 123
    created_tweet_mock = MagicMock(spec=Tweet)
    created_tweet_mock.id = tweet_id
    mock_tweet_service.create_tweet.return_value = created_tweet_mock

    # Вызываем обработчик
    result = await create_tweet(
        db=mock_db_session,
        current_user=test_user_obj,
        tweet_service=mock_tweet_service,
        tweet_in=tweet_in_data,
    )

    # Проверяем вызов сервиса
    mock_tweet_service.create_tweet.assert_awaited_once_with(
        db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_in_data
    )
    # Проверяем результат
    assert isinstance(result, TweetCreateResult)
    assert result.tweet_id == tweet_id


# --- Тест для delete_tweet ---

async def test_delete_tweet_handler(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_service: MagicMock,
):
    """Юнит-тест для обработчика delete_tweet."""
    tweet_id_to_delete = 456
    # Настраиваем мок сервиса (метод ничего не возвращает)
    mock_tweet_service.delete_tweet.return_value = None

    # Вызываем обработчик
    result = await delete_tweet(
        db=mock_db_session,
        current_user=test_user_obj,
        tweet_service=mock_tweet_service,
        tweet_id=tweet_id_to_delete,  # Передаем Path параметр напрямую
    )

    # Проверяем вызов сервиса
    mock_tweet_service.delete_tweet.assert_awaited_once_with(
        db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id_to_delete
    )
    # Проверяем результат
    assert isinstance(result, TweetActionResult)
    assert result.result is True


# --- Тест для like_tweet ---

async def test_like_tweet_handler(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_like_service: MagicMock,
):
    """Юнит-тест для обработчика like_tweet."""
    tweet_id_to_like = 789
    # Настраиваем мок сервиса
    mock_like_service.like_tweet.return_value = None

    # Вызываем обработчик
    result = await like_tweet(
        db=mock_db_session,
        current_user=test_user_obj,
        like_service=mock_like_service,
        tweet_id=tweet_id_to_like,
    )

    # Проверяем вызов сервиса
    mock_like_service.like_tweet.assert_awaited_once_with(
        db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id_to_like
    )
    # Проверяем результат
    assert isinstance(result, TweetActionResult)
    assert result.result is True


# --- Тест для unlike_tweet ---

async def test_unlike_tweet_handler(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_like_service: MagicMock,
):
    """Юнит-тест для обработчика unlike_tweet."""
    tweet_id_to_unlike = 101
    # Настраиваем мок сервиса
    mock_like_service.unlike_tweet.return_value = None

    # Вызываем обработчик
    result = await unlike_tweet(
        db=mock_db_session,
        current_user=test_user_obj,
        like_service=mock_like_service,
        tweet_id=tweet_id_to_unlike,
    )

    # Проверяем вызов сервиса
    mock_like_service.unlike_tweet.assert_awaited_once_with(
        db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id_to_unlike
    )
    # Проверяем результат
    assert isinstance(result, TweetActionResult)
    assert result.result is True
