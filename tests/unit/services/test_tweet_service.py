# tests/unit/services/test_tweet_service.py
from unittest.mock import AsyncMock, MagicMock, call, patch  # Добавим patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.core.exceptions import (BadRequestError, ConflictError,
                                 NotFoundError, PermissionDeniedError)
from src.models import Follow, Like, Media, Tweet, User
from src.repositories import (FollowRepository, MediaRepository,
                              TweetRepository)
from src.schemas.tweet import (LikeInfo, TweetAuthor, TweetCreateRequest,
                               TweetFeedResult, TweetInFeed)
from src.services.media_service import MediaService  # Нужен мок MediaService
from src.services.tweet_service import TweetService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---
@pytest.fixture
def mock_tweet_repo() -> MagicMock:
    repo = MagicMock(spec=TweetRepository)
    repo.get_with_attachments = AsyncMock()
    repo.delete = AsyncMock()
    repo.get_feed_for_user = AsyncMock()
    # Базовый репозиторий для create
    repo.model = Tweet
    repo.add = AsyncMock()  # Метод add используется в create_tweet через self.add
    return repo


@pytest.fixture
def mock_follow_repo() -> MagicMock:
    repo = MagicMock(spec=FollowRepository)
    repo.get_following_ids = AsyncMock()
    return repo


@pytest.fixture
def mock_media_repo() -> MagicMock:
    repo = MagicMock(spec=MediaRepository)
    repo.get = AsyncMock()
    repo.delete = AsyncMock()  # Для упрощенной логики удаления 1:N
    return repo


@pytest.fixture
def mock_media_service() -> MagicMock:
    service = MagicMock(spec=MediaService)
    service.get_media_url = MagicMock()
    service.delete_media_files = AsyncMock()
    return service


@pytest.fixture
def tweet_service(
        mock_tweet_repo: MagicMock,
        mock_follow_repo: MagicMock,
        mock_media_repo: MagicMock,
        mock_media_service: MagicMock,
) -> TweetService:
    service = TweetService(
        repo=mock_tweet_repo,
        follow_repo=mock_follow_repo,
        media_repo=mock_media_repo,
        media_service=mock_media_service
    )
    # Сохраняем моки
    service._mock_tweet_repo = mock_tweet_repo
    service._mock_follow_repo = mock_follow_repo
    service._mock_media_repo = mock_media_repo
    service._mock_media_service = mock_media_service
    return service


# --- Тесты для create_tweet ---

async def test_create_tweet_success_no_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User
):
    """Тест успешного создания твита без медиа."""
    tweet_content = "Simple tweet"
    request_data = TweetCreateRequest(tweet_data=tweet_content, tweet_media_ids=None)

    # Мок для db.add внутри repo.add
    # Мок для db.flush
    # Мок для db.commit
    # Мок для db.refresh

    # Вызываем метод
    created_tweet = await tweet_service.create_tweet(
        db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
    )

    # Проверки
    assert isinstance(created_tweet, Tweet)
    assert created_tweet.content == tweet_content
    assert created_tweet.author_id == test_user_obj.id

    # Проверяем вызовы репозитория (через repo.add) и сессии
    tweet_service._mock_tweet_repo.add.assert_awaited_once()
    # Проверяем, что был создан правильный объект Tweet
    added_tweet_arg = tweet_service._mock_tweet_repo.add.await_args[0][1]  # db_obj=...
    assert isinstance(added_tweet_arg, Tweet)
    assert added_tweet_arg.content == tweet_content
    assert added_tweet_arg.author_id == test_user_obj.id

    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()  # Проверяем refresh
    mock_db_session.rollback.assert_not_awaited()
    # media_repo не должен был вызываться
    tweet_service._mock_media_repo.get.assert_not_awaited()


async def test_create_tweet_success_with_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_media_obj: Media  # Медиа объект для мока
):
    """Тест успешного создания твита с медиа."""
    tweet_content = "Tweet with media"
    media_id = test_media_obj.id
    request_data = TweetCreateRequest(tweet_data=tweet_content, tweet_media_ids=[media_id])

    # Убедимся, что у мока медиа tweet_id=None
    test_media_obj.tweet_id = None

    # Настраиваем моки
    tweet_service._mock_media_repo.get.return_value = test_media_obj

    # Вызываем метод
    created_tweet = await tweet_service.create_tweet(
        db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
    )

    # Проверки
    assert isinstance(created_tweet, Tweet)
    # Проверяем вызовы
    tweet_service._mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    tweet_service._mock_tweet_repo.add.assert_awaited_once()
    # Проверяем, что у объекта media установился tweet_id *после* flush и *перед* commit
    # Это сложно проверить напрямую с моками, но проверяем commit
    assert test_media_obj.tweet_id == created_tweet.id  # Проверяем, что ID был присвоен

    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()
    mock_db_session.rollback.assert_not_awaited()


async def test_create_tweet_media_not_found(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
):
    """Тест создания твита, когда медиа не найдено."""
    media_id = 999
    request_data = TweetCreateRequest(tweet_data="Bad media", tweet_media_ids=[media_id])

    # Настраиваем мок
    tweet_service._mock_media_repo.get.return_value = None  # Медиа не найдено

    # Проверяем исключение
    with pytest.raises(NotFoundError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
        )

    # Проверки вызовов
    tweet_service._mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    tweet_service._mock_tweet_repo.add.assert_not_awaited()
    mock_db_session.flush.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть откат


async def test_create_tweet_media_already_used(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_media_obj: Media
):
    """Тест создания твита, когда медиа уже привязано к другому твиту."""
    media_id = test_media_obj.id
    request_data = TweetCreateRequest(tweet_data="Used media", tweet_media_ids=[media_id])

    # Имитируем, что медиа уже привязано
    test_media_obj.tweet_id = 555  # Привязано к твиту 555

    # Настраиваем мок
    tweet_service._mock_media_repo.get.return_value = test_media_obj

    # Проверяем исключение
    with pytest.raises(ConflictError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
        )

    # Проверки вызовов
    tweet_service._mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    tweet_service._mock_tweet_repo.add.assert_not_awaited()
    mock_db_session.flush.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()


# --- Тесты для delete_tweet ---

async def test_delete_tweet_success_no_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet  # Твит без медиа
):
    """Тест успешного удаления твита без медиа."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_user_obj.id  # Убедимся, что автор правильный
    test_tweet_obj.attachments = []  # Явно указываем, что медиа нет

    # Настраиваем мок
    tweet_service._mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj

    # Вызываем метод
    await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверки вызовов
    tweet_service._mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    tweet_service._mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=test_tweet_obj)
    mock_db_session.commit.assert_awaited_once()
    tweet_service._mock_media_service.delete_media_files.assert_not_awaited()  # Файлы не удаляем
    mock_db_session.rollback.assert_not_awaited()


async def test_delete_tweet_success_with_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,  # Твит
        test_media_obj: Media  # Медиа
):
    """Тест успешного удаления твита с медиа."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_user_obj.id
    # Привязываем медиа к твиту
    test_media_obj.tweet_id = tweet_id
    test_media_obj.file_path = "path/to/delete.jpg"
    test_tweet_obj.attachments = [test_media_obj]  # Имитируем загруженную связь

    # Настраиваем мок
    tweet_service._mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj

    # Вызываем метод
    await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверки вызовов
    tweet_service._mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    tweet_service._mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=test_tweet_obj)
    mock_db_session.commit.assert_awaited_once()
    # Проверяем удаление файлов ПОСЛЕ коммита
    tweet_service._mock_media_service.delete_media_files.assert_awaited_once_with([test_media_obj.file_path])
    mock_db_session.rollback.assert_not_awaited()


async def test_delete_tweet_not_found(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
):
    """Тест удаления несуществующего твита."""
    tweet_id = 999
    # Настраиваем мок
    tweet_service._mock_tweet_repo.get_with_attachments.return_value = None

    # Проверяем исключение
    with pytest.raises(NotFoundError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверки вызовов
    tweet_service._mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    tweet_service._mock_tweet_repo.delete.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Роллбэк из-за исключения до commit


async def test_delete_tweet_permission_denied(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,  # Текущий пользователь
        test_tweet_obj: Tweet,  # Твит другого пользователя
        test_alice_obj: User  # Автор твита
):
    """Тест попытки удалить чужой твит."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_alice_obj.id  # Автор - Алиса

    # Настраиваем мок
    tweet_service._mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj

    # Проверяем исключение
    with pytest.raises(PermissionDeniedError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверки вызовов
    tweet_service._mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    tweet_service._mock_tweet_repo.delete.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()


# --- Тесты для get_tweet_feed ---

async def test_get_tweet_feed_success(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,  # Пользователь, на которого подписаны
        test_tweet_obj: Tweet,  # Твит Алисы
        test_media_obj: Media,  # Медиа для твита Алисы
        test_like_obj: Like,  # Лайк от test_user_obj на твит Алисы
):
    """Тест успешного получения ленты."""
    # Настраиваем данные
    test_tweet_obj.author = test_alice_obj  # Привязываем автора
    test_media_obj.file_path = "alice/pic.jpg"
    test_tweet_obj.attachments = [test_media_obj]  # Привязываем медиа
    test_like_obj.user = test_user_obj  # Привязываем юзера к лайку
    test_tweet_obj.likes = [test_like_obj]  # Привязываем лайк

    # Настраиваем моки
    tweet_service._mock_follow_repo.get_following_ids.return_value = [test_alice_obj.id]  # Подписан на Алису
    # Репозиторий возвращает твит Алисы (включая твиты самого юзера - здесь один от Алисы)
    tweet_service._mock_tweet_repo.get_feed_for_user.return_value = [test_tweet_obj]
    # Медиа сервис возвращает URL
    expected_media_url = "/media/alice/pic.jpg"
    tweet_service._mock_media_service.get_media_url.return_value = expected_media_url

    # Вызываем метод
    feed_result = await tweet_service.get_tweet_feed(db=mock_db_session, current_user=test_user_obj)

    # Проверки
    assert isinstance(feed_result, TweetFeedResult)
    assert feed_result.result is True
    assert len(feed_result.tweets) == 1

    tweet_in_feed = feed_result.tweets[0]
    assert isinstance(tweet_in_feed, TweetInFeed)
    assert tweet_in_feed.id == test_tweet_obj.id
    assert tweet_in_feed.content == test_tweet_obj.content

    # Проверка автора
    assert isinstance(tweet_in_feed.author, TweetAuthor)
    assert tweet_in_feed.author.id == test_alice_obj.id
    assert tweet_in_feed.author.name == test_alice_obj.name

    # Проверка лайков (с алиасом user_id)
    assert len(tweet_in_feed.likes) == 1
    assert isinstance(tweet_in_feed.likes[0], LikeInfo)
    # Проверяем сериализацию с алиасом
    like_dict = tweet_in_feed.likes[0].model_dump(by_alias=True)
    assert like_dict["user_id"] == test_user_obj.id
    assert like_dict["name"] == test_user_obj.name

    # Проверка медиа
    assert len(tweet_in_feed.attachments) == 1
    assert tweet_in_feed.attachments[0] == expected_media_url

    # Проверка вызовов
    tweet_service._mock_follow_repo.get_following_ids.assert_awaited_once_with(mock_db_session,
                                                                               follower_id=test_user_obj.id)
    # Проверяем, что ID текущего пользователя был добавлен к списку ID для запроса
    expected_author_ids = list(set([test_alice_obj.id] + [test_user_obj.id]))
    tweet_service._mock_tweet_repo.get_feed_for_user.assert_awaited_once_with(mock_db_session,
                                                                              author_ids=expected_author_ids)
    tweet_service._mock_media_service.get_media_url.assert_called_once_with(test_media_obj)


async def test_get_tweet_feed_empty(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
):
    """Тест получения пустой ленты."""
    # Настраиваем моки
    tweet_service._mock_follow_repo.get_following_ids.return_value = []  # Не подписан ни на кого
    # Репозиторий возвращает пустой список (только для ID текущего пользователя)
    tweet_service._mock_tweet_repo.get_feed_for_user.return_value = []

    # Вызываем метод
    feed_result = await tweet_service.get_tweet_feed(db=mock_db_session, current_user=test_user_obj)

    # Проверки
    assert isinstance(feed_result, TweetFeedResult)
    assert feed_result.tweets == []

    # Проверка вызовов
    tweet_service._mock_follow_repo.get_following_ids.assert_awaited_once_with(mock_db_session,
                                                                               follower_id=test_user_obj.id)
    expected_author_ids = [test_user_obj.id]  # Только свой ID
    tweet_service._mock_tweet_repo.get_feed_for_user.assert_awaited_once_with(mock_db_session,
                                                                              author_ids=expected_author_ids)
    tweet_service._mock_media_service.get_media_url.assert_not_called()  # Нет твитов - нет вызовов
