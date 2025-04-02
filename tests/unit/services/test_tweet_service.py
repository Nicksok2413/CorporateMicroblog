"""Юнит-тесты для TweetService."""

import pytest
from unittest.mock import AsyncMock, MagicMock  # Используем AsyncMock для асинхронных методов репозитория

# Импортируем сервисы, модели, схемы, исключения
from app.services.tweet_service import tweet_service
from app.models import User, Tweet, Media
from app.schemas.tweet import TweetCreateRequest
from app.core.exceptions import NotFoundError, PermissionDeniedError


# --- Тесты для create_tweet ---

@pytest.mark.asyncio
async def test_create_tweet_service_success(mocker):  # mocker предоставляется pytest-mock
    """Тест успешного создания твита через сервис."""
    # 1. Мокируем зависимости (репозитории)
    mock_tweet_repo = mocker.patch("app.services.tweet_service.tweet_repo", autospec=True)
    mock_media_repo = mocker.patch("app.services.tweet_service.media_repo",
                                   autospec=True)  # Используется в create_tweet

    # Настраиваем возвращаемые значения моков
    mock_tweet_repo.create_with_author_and_media.return_value = Tweet(id=1, content="Test", author_id=1)
    # Медиа не запрашиваем в этом тесте

    # 2. Готовим входные данные
    db_session_mock = AsyncMock()  # Мок сессии БД (не используется напрямую в этом тесте)
    current_user = User(id=1, name="Test", api_key="testkey")
    tweet_data = TweetCreateRequest(tweet_data="Test")

    # 3. Вызываем метод сервиса
    created_tweet = await tweet_service.create_tweet(
        db=db_session_mock, tweet_data=tweet_data, current_user=current_user
    )

    # 4. Проверяем результат
    assert created_tweet is not None
    assert created_tweet.id == 1
    assert created_tweet.content == "Test"
    # Проверяем, что метод репозитория был вызван с правильными аргументами
    mock_tweet_repo.create_with_author_and_media.assert_called_once_with(
        db=db_session_mock,
        content="Test",
        author_id=current_user.id,
        media_items=[]  # Ожидаем пустой список, т.к. media_ids не переданы
    )
    # Проверяем, что media_repo.get не вызывался
    mock_media_repo.get.assert_not_called()


@pytest.mark.asyncio
async def test_create_tweet_service_with_media_success(mocker):
    """Тест успешного создания твита с медиа."""
    mock_tweet_repo = mocker.patch("app.services.tweet_service.tweet_repo", autospec=True)
    mock_media_repo = mocker.patch("app.services.tweet_service.media_repo", autospec=True)

    # Мок для медиа, которое будет найдено
    found_media = Media(id=10, file_path="test.jpg")
    mock_media_repo.get.return_value = found_media
    mock_tweet_repo.create_with_author_and_media.return_value = Tweet(id=2, content="With Media", author_id=1)

    db_session_mock = AsyncMock()
    current_user = User(id=1, name="Test", api_key="testkey")
    tweet_data = TweetCreateRequest(tweet_data="With Media", tweet_media_ids=[10])

    created_tweet = await tweet_service.create_tweet(
        db=db_session_mock, tweet_data=tweet_data, current_user=current_user
    )

    assert created_tweet is not None
    assert created_tweet.id == 2
    # Проверяем вызовы репозиториев
    mock_media_repo.get.assert_called_once_with(db_session_mock, id=10)
    mock_tweet_repo.create_with_author_and_media.assert_called_once_with(
        db=db_session_mock,
        content="With Media",
        author_id=current_user.id,
        media_items=[found_media]  # Ожидаем список с найденным медиа
    )


@pytest.mark.asyncio
async def test_create_tweet_service_media_not_found(mocker):
    """Тест создания твита с несуществующим media_id."""
    mock_tweet_repo = mocker.patch("app.services.tweet_service.tweet_repo", autospec=True)
    mock_media_repo = mocker.patch("app.services.tweet_service.media_repo", autospec=True)

    # Настраиваем мок media_repo.get, чтобы он вернул None
    mock_media_repo.get.return_value = None

    db_session_mock = AsyncMock()
    current_user = User(id=1, name="Test", api_key="testkey")
    tweet_data = TweetCreateRequest(tweet_data="Should fail", tweet_media_ids=[99])

    # Проверяем, что выбрасывается правильное исключение
    with pytest.raises(NotFoundError) as exc_info:
        await tweet_service.create_tweet(
            db=db_session_mock, tweet_data=tweet_data, current_user=current_user
        )

    assert "Медиафайл с ID 99 не найден" in str(exc_info.value)
    # Проверяем, что create_with_author_and_media не вызывался
    mock_tweet_repo.create_with_author_and_media.assert_not_called()


# --- Тесты для delete_tweet ---

@pytest.mark.asyncio
async def test_delete_tweet_service_success(mocker):
    """Тест успешного удаления твита владельцем."""
    mock_tweet_repo = mocker.patch("app.services.tweet_service.tweet_repo", autospec=True)

    # Твит, который будет "найден" репозиторием
    existing_tweet = Tweet(id=5, content="Delete me", author_id=1)
    mock_tweet_repo.get.return_value = existing_tweet
    mock_tweet_repo.remove.return_value = existing_tweet  # Mock remove confirmation

    db_session_mock = AsyncMock()
    current_user = User(id=1, name="Test", api_key="testkey")  # Владелец твита

    # Вызываем метод сервиса - не должно быть исключений
    await tweet_service.delete_tweet(db=db_session_mock, tweet_id=5, current_user=current_user)

    # Проверяем вызовы репозитория
    mock_tweet_repo.get.assert_called_once_with(db_session_mock, id=5)
    mock_tweet_repo.remove.assert_called_once_with(db=db_session_mock, id=5)


@pytest.mark.asyncio
async def test_delete_tweet_service_not_found(mocker):
    """Тест удаления несуществующего твита."""
    mock_tweet_repo = mocker.patch("app.services.tweet_service.tweet_repo", autospec=True)
    mock_tweet_repo.get.return_value = None  # Твит не найден

    db_session_mock = AsyncMock()
    current_user = User(id=1, name="Test", api_key="testkey")

    with pytest.raises(NotFoundError) as exc_info:
        await tweet_service.delete_tweet(db=db_session_mock, tweet_id=99, current_user=current_user)

    assert "Твит с ID 99 не найден" in str(exc_info.value)
    mock_tweet_repo.remove.assert_not_called()


@pytest.mark.asyncio
async def test_delete_tweet_service_forbidden(mocker):
    """Тест попытки удаления чужого твита."""
    mock_tweet_repo = mocker.patch("app.services.tweet_service.tweet_repo", autospec=True)

    existing_tweet = Tweet(id=6, content="Someone else's tweet", author_id=2)  # Автор ID 2
    mock_tweet_repo.get.return_value = existing_tweet

    db_session_mock = AsyncMock()
    current_user = User(id=1, name="Test", api_key="testkey")  # Текущий пользователь ID 1

    with pytest.raises(PermissionDeniedError) as exc_info:
        await tweet_service.delete_tweet(db=db_session_mock, tweet_id=6, current_user=current_user)

    assert "Вы не можете удалить этот твит" in str(exc_info.value)
    mock_tweet_repo.remove.assert_not_called()

# TODO: Добавить юнит-тесты для like_tweet, unlike_tweet, get_tweet_feed
# TODO: Добавить юнит-тесты для других сервисов (UserService, MediaService, FollowService)
