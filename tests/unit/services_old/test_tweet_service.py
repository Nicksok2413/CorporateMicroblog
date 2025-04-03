"""Юнит-тесты для TweetService."""

import pytest
from unittest.mock import AsyncMock

from app.services.tweet_service import tweet_service
from app.models import User, Tweet, Media, Like
from app.schemas.tweet import TweetFeedResult
from app.core.exceptions import NotFoundError, ConflictError


# --- Тесты для create_tweet (как раньше) ---
# ... (test_create_tweet_service_success, test_create_tweet_service_with_media_success, ...)

# --- Тесты для delete_tweet (как раньше) ---
# ... (test_delete_tweet_service_success, test_delete_tweet_service_not_found, ...)

# --- Тесты для like_tweet ---

@pytest.mark.asyncio
async def test_like_tweet_service_success(mocker):
    """Тест успешного лайка."""
    mock_tweet_repo = mocker.patch("app.services_old.tweet_service.tweet_repo", autospec=True)
    mock_like_repo = mocker.patch("app.services_old.tweet_service.like_repo", autospec=True)

    # Настраиваем моки
    mock_tweet_repo.get.return_value = Tweet(id=1, author_id=2)  # Твит существует
    mock_like_repo.get_like.return_value = None  # Лайка еще нет
    mock_like_repo.create_like.return_value = Like(user_id=1, tweet_id=1)  # Успешное создание

    db_session_mock = AsyncMock()
    current_user = User(id=1)

    # Вызов - не должно быть исключений
    await tweet_service.like_tweet(db=db_session_mock, current_user=current_user, tweet_id=1)

    # Проверки
    mock_tweet_repo.get.assert_called_once_with(db_session_mock, id=1)
    mock_like_repo.get_like.assert_called_once_with(db=db_session_mock, user_id=1, tweet_id=1)
    mock_like_repo.create_like.assert_called_once_with(db=db_session_mock, user_id=1, tweet_id=1)


@pytest.mark.asyncio
async def test_like_tweet_service_already_liked(mocker):
    """Тест лайка уже лайкнутого твита."""
    mock_tweet_repo = mocker.patch("app.services_old.tweet_service.tweet_repo", autospec=True)
    mock_like_repo = mocker.patch("app.services_old.tweet_service.like_repo", autospec=True)

    mock_tweet_repo.get.return_value = Tweet(id=1, author_id=2)
    mock_like_repo.get_like.return_value = Like(user_id=1, tweet_id=1)  # Лайк уже есть

    db_session_mock = AsyncMock()
    current_user = User(id=1)

    with pytest.raises(ConflictError):
        await tweet_service.like_tweet(db=db_session_mock, current_user=current_user, tweet_id=1)

    mock_like_repo.create_like.assert_not_called()


@pytest.mark.asyncio
async def test_like_tweet_service_tweet_not_found(mocker):
    """Тест лайка несуществующего твита."""
    mock_tweet_repo = mocker.patch("app.services_old.tweet_service.tweet_repo", autospec=True)
    mock_like_repo = mocker.patch("app.services_old.tweet_service.like_repo", autospec=True)

    mock_tweet_repo.get.return_value = None  # Твит не найден

    db_session_mock = AsyncMock()
    current_user = User(id=1)

    with pytest.raises(NotFoundError):
        await tweet_service.like_tweet(db=db_session_mock, current_user=current_user, tweet_id=99)

    mock_like_repo.get_like.assert_not_called()
    mock_like_repo.create_like.assert_not_called()


# --- Тесты для unlike_tweet ---

@pytest.mark.asyncio
async def test_unlike_tweet_service_success(mocker):
    """Тест успешного снятия лайка."""
    mock_like_repo = mocker.patch("app.services_old.tweet_service.like_repo", autospec=True)
    mock_like_repo.remove_like.return_value = True  # Лайк найден и удален

    db_session_mock = AsyncMock()
    current_user = User(id=1)

    await tweet_service.unlike_tweet(db=db_session_mock, current_user=current_user, tweet_id=1)

    mock_like_repo.remove_like.assert_called_once_with(db=db_session_mock, user_id=1, tweet_id=1)


@pytest.mark.asyncio
async def test_unlike_tweet_service_not_liked(mocker):
    """Тест снятия лайка, которого не было."""
    mock_like_repo = mocker.patch("app.services_old.tweet_service.like_repo", autospec=True)
    mock_like_repo.remove_like.return_value = False  # Лайк не найден

    db_session_mock = AsyncMock()
    current_user = User(id=1)

    with pytest.raises(NotFoundError):
        await tweet_service.unlike_tweet(db=db_session_mock, current_user=current_user, tweet_id=1)

    mock_like_repo.remove_like.assert_called_once_with(db=db_session_mock, user_id=1, tweet_id=1)


# --- Тесты для get_tweet_feed ---

@pytest.mark.asyncio
async def test_get_tweet_feed_service_success(mocker):
    """Тест успешного получения ленты."""
    # Мокируем все используемые репозитории и сервисы
    mock_follow_repo = mocker.patch("app.services_old.tweet_service.follow_repo", autospec=True)
    mock_tweet_repo = mocker.patch("app.services_old.tweet_service.tweet_repo", autospec=True)
    # Мокируем media_service.get_media_url, т.к. он используется для форматирования
    mock_media_service = mocker.patch("app.services_old.tweet_service.media_service", autospec=True)

    # Подготовка данных
    current_user = User(id=1, name="Alice")
    author_bob = User(id=2, name="Bob")
    following_ids = [2]  # Alice подписана на Bob (ID 2)
    author_ids_expected = [2, 1]  # Ожидаем ID Боба и Алисы

    media1 = Media(id=10, file_path="img1.jpg")
    tweet1_by_bob = Tweet(id=101, content="Bob's tweet", author_id=2, author=author_bob, likes=[], attachments=[media1])
    tweet2_by_alice = Tweet(id=102, content="Alice's tweet", author_id=1, author=current_user, likes=[], attachments=[])
    db_tweets = [tweet1_by_bob, tweet2_by_alice]  # Твиты, которые вернет репозиторий

    # Настройка моков
    mock_follow_repo.get_following_ids.return_value = following_ids
    mock_tweet_repo.get_feed_for_user.return_value = db_tweets
    mock_media_service.get_media_url.side_effect = lambda \
        media: f"/static/media/{media.file_path}"  # Простая реализация мока

    db_session_mock = AsyncMock()

    # Вызов сервиса
    result: TweetFeedResult = await tweet_service.get_tweet_feed(db=db_session_mock, current_user=current_user)

    # Проверки
    mock_follow_repo.get_following_ids.assert_called_once_with(db=db_session_mock, follower_id=current_user.id)
    # Проверяем, что get_feed_for_user вызван с правильным набором ID
    mock_tweet_repo.get_feed_for_user.assert_called_once()
    call_args, call_kwargs = mock_tweet_repo.get_feed_for_user.call_args
    assert call_kwargs['db'] == db_session_mock
    # Сравниваем множества ID, т.к. порядок не важен
    assert set(call_kwargs['author_ids']) == set(author_ids_expected)

    # Проверка результата
    assert result is not None
    assert isinstance(result, TweetFeedResult)
    assert len(result.tweets) == 2

    # Проверка форматирования первого твита (Боба)
    formatted_tweet1 = result.tweets[0]
    assert formatted_tweet1.id == 101
    assert formatted_tweet1.author.id == 2
    assert formatted_tweet1.author.name == "Bob"
    assert len(formatted_tweet1.attachments) == 1
    assert formatted_tweet1.attachments[0] == "/static/media/img1.jpg"
    assert len(formatted_tweet1.likes) == 0

    # Проверка форматирования второго твита (Алисы)
    formatted_tweet2 = result.tweets[1]
    assert formatted_tweet2.id == 102
    assert formatted_tweet2.author.id == 1
    assert formatted_tweet2.author.name == "Alice"
    assert len(formatted_tweet2.attachments) == 0

    # Проверка, сколько раз вызывался get_media_url
    assert mock_media_service.get_media_url.call_count == 1
    mock_media_service.get_media_url.assert_called_with(media1)
