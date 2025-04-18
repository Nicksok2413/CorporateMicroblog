from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError  # Для имитации ошибок БД

from src.core.exceptions import (
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from src.models import Like, Media, Tweet, User
from src.schemas.tweet import (
    LikeInfo,
    TweetAuthor,
    TweetCreateRequest,
    TweetFeedResult,
    TweetInFeed,
)
from src.services.tweet_service import TweetService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---

# Фикстура для создания экземпляра сервиса
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
    return service


# --- Тесты для create_tweet ---

async def test_create_tweet_success_no_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
        mock_media_repo: MagicMock,
):
    """Тест успешного создания твита без медиа."""
    request_data = TweetCreateRequest(tweet_data="Simple tweet", tweet_media_ids=[])

    # Вызываем метод сервиса
    created_tweet = await tweet_service.create_tweet(
        db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
    )

    # Проверки
    assert created_tweet is not None
    assert isinstance(created_tweet, Tweet)
    assert created_tweet.content == request_data.tweet_data
    assert created_tweet.author_id == test_user_obj.id

    # Проверяем, что repo.create не вызывался
    mock_tweet_repo.create.assert_not_awaited()

    # Проверяем, что repo.add вызывался (через сессию)
    mock_tweet_repo.add.assert_called_once()  # Проверяем что объект Tweet добавлен в сессию
    mock_db_session.flush.assert_awaited_once()  # Должен быть flush
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.refresh.assert_awaited_once()  # Должен быть refresh
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно

    # Проверяем, что media_repo.get не вызывался
    mock_media_repo.get.assert_not_awaited()


async def test_create_tweet_success_with_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_media_obj: Media,
        mock_media_repo: MagicMock,
):
    """Тест успешного создания твита с одним медиа."""
    media_id = test_media_obj.id
    request_data = TweetCreateRequest(
        tweet_data="Tweet with media", tweet_media_ids=[media_id]
    )

    # Убедимся, что у мока медиа tweet_id is None
    test_media_obj.tweet_id = None

    # Настраиваем моки
    # media_repo.get находит медиа, и оно не привязано (tweet_id is None)
    mock_media_repo.get.return_value = test_media_obj

    # Вызываем метод сервиса
    created_tweet = await tweet_service.create_tweet(
        db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
    )

    # Проверки
    assert created_tweet is not None
    assert isinstance(created_tweet, Tweet)

    # Проверяем вызов media_repo.get
    mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)

    # Проверяем, что tweet_id у медиа объекта был обновлен
    assert test_media_obj.tweet_id == created_tweet.id

    # Проверяем вызовы
    mock_db_session.flush.assert_awaited_once()  # Должен быть flush
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.refresh.assert_awaited_once()  # Должен быть refresh
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_create_tweet_media_not_found(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_media_repo: MagicMock,
):
    """Тест создания твита, когда медиа не найден."""
    media_id = 999
    request_data = TweetCreateRequest(
        tweet_data="Tweet with bad media", tweet_media_ids=[media_id]
    )

    # Настраиваем мок - медиа не найдено
    mock_media_repo.get.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=request_data
        )

    # Проверяем вызовы
    mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    mock_db_session.add.assert_not_called()  # Не должны дойти до создания твита
    mock_db_session.flush.assert_not_awaited()  # flush быть не должно
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


async def test_create_tweet_db_error_on_flush(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
):
    """Тест ошибки БД при flush (например, при получении ID твита)."""
    tweet_data_req = TweetCreateRequest(tweet_data="Simple tweet", tweet_media_ids=[])

    # Имитируем ошибку на flush
    mock_db_session.flush.side_effect = SQLAlchemyError("Flush error")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_data_req
        )

    # Проверяем вызовы
    mock_tweet_repo.add.assert_called_once()  # Проверяем что объект Tweet добавлен в сессию
    mock_db_session.flush.assert_awaited_once()  # Должен быть flush
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


# --- Тесты для delete_tweet ---

async def test_delete_tweet_success_no_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,  # Твит без медиа по фикстуре
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест успешного удаления твита без медиа."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_user_obj.id  # Убедимся, что автор правильный

    # get_with_attachments вернет твит без медиа
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    # delete ничего не возвращает
    mock_tweet_repo.delete.return_value = None

    # Вызываем метод сервиса
    await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, tweet_id=tweet_id)
    mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=test_tweet_obj)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_media_service.delete_media_files.assert_not_awaited()  # Проверяем, что delete_media_files не вызывался
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_delete_tweet_success_with_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        test_media_obj: Media,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест успешного удаления твита с медиа."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_user_obj.id

    # Привязываем медиа к твиту
    test_media_obj.tweet_id = tweet_id
    test_media_obj.file_path = "path/to/delete.jpg"
    test_tweet_obj.attachments = [test_media_obj]  # Имитируем загруженную связь

    # Настраиваем моки
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    mock_tweet_repo.delete.return_value = None
    mock_media_service.delete_media_files.return_value = None

    # Вызываем метод сервиса
    await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, tweet_id=tweet_id)
    mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=test_tweet_obj)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит

    # Проверяем удаление файлов после коммита
    expected_paths = [test_media_obj.file_path]
    mock_media_service.delete_media_files.assert_awaited_once_with(expected_paths)
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_delete_tweet_not_found(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест удаления несуществующего твита."""
    tweet_id = 999
    # Настраиваем мок
    mock_tweet_repo.get_with_attachments.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, tweet_id=tweet_id)
    mock_tweet_repo.delete.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_media_service.delete_media_files.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк (хотя ошибка до изменений)


async def test_delete_tweet_permission_denied(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,  # Другой пользователь
        test_tweet_obj: Tweet,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест попытки удаления чужого твита."""
    tweet_id = test_tweet_obj.id
    # Автор твита - alice, а удаляет - test_user
    test_tweet_obj.author_id = test_alice_obj.id
    # Настраиваем мок
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj

    # Проверяем, что выбрасывается PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, tweet_id=tweet_id)
    mock_tweet_repo.delete.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_media_service.delete_media_files.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


async def test_delete_tweet_db_error_on_commit(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест ошибки БД при коммите удаления."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_user_obj.id
    # Настраиваем моки
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    # Имитируем ошибку на commit
    mock_db_session.commit.side_effect = SQLAlchemyError("Commit failed")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверяем вызовы
    mock_tweet_repo.get_with_attachments.assert_awaited_once()
    mock_tweet_repo.delete.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк
    mock_media_service.delete_media_files.assert_not_awaited()  # Не должны удалять файлы


async def test_delete_tweet_file_delete_error(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_tweet_obj: Tweet,
        test_media_obj: Media,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест ошибки при удалении файла после успешного коммита БД."""
    tweet_id = test_tweet_obj.id
    test_tweet_obj.author_id = test_user_obj.id
    test_media_obj.tweet_id = tweet_id
    test_tweet_obj.attachments = [test_media_obj]

    # Настраиваем моки
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    # Успешный коммит
    mock_db_session.commit.return_value = None
    # Ошибка при удалении файла
    file_error_message = "Cannot delete file"
    mock_media_service.delete_media_files.side_effect = Exception(file_error_message)

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError) as exc_info:
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    assert "ошибка при удалении его медиафайлов" in exc_info.value.detail

    # Проверяем вызовы
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно

    # Проверяем вызов удаления файлов
    expected_paths = [test_media_obj.file_path]
    mock_media_service.delete_media_files.assert_awaited_once_with(expected_paths)


# --- Тесты для get_tweet_feed ---

async def test_get_tweet_feed_success(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,  # Пользователь, на которого подписаны
        test_tweet_obj: Tweet,  # Твит Алисы
        test_media_obj: Media,  # Медиа для твита Алисы
        test_like_obj: Like,  # Лайк от test_user_obj на твит Алисы
        mock_tweet_repo: MagicMock,
        mock_follow_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест успешного получения ленты."""
    # Настраиваем данные
    test_tweet_obj.author = test_alice_obj  # Привязываем автора
    test_media_obj.file_path = "alice/pic.jpg"
    test_tweet_obj.attachments = [test_media_obj]  # Привязываем медиа
    test_like_obj.user = test_user_obj  # Привязываем юзера к лайку
    test_tweet_obj.likes = [test_like_obj]  # Привязываем лайк

    # Настраиваем моки
    mock_follow_repo.get_following_ids.return_value = [test_alice_obj.id]  # Подписан на Алису
    # Репозиторий возвращает твит Алисы (включая твиты самого юзера - здесь один от Алисы)
    mock_tweet_repo.get_feed_for_user.return_value = [test_tweet_obj]
    # Медиа сервис возвращает URL
    expected_media_url = "/media/alice/pic.jpg"
    mock_media_service.get_media_url.return_value = expected_media_url

    # Вызываем метод сервиса
    feed_result = await tweet_service.get_tweet_feed(db=mock_db_session, current_user=test_user_obj)

    # Проверки
    assert isinstance(feed_result, TweetFeedResult)
    assert feed_result.result is True
    assert len(feed_result.tweets) == 1

    # Проверка твита
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
    mock_follow_repo.get_following_ids.assert_awaited_once_with(mock_db_session,
                                                                follower_id=test_user_obj.id)
    # Проверяем, что ID текущего пользователя был добавлен к списку ID для запроса
    expected_author_ids = list(set([test_alice_obj.id] + [test_user_obj.id]))
    mock_tweet_repo.get_feed_for_user.assert_awaited_once_with(mock_db_session,
                                                               author_ids=expected_author_ids)
    mock_media_service.get_media_url.assert_called_once_with(test_media_obj)


async def test_get_tweet_feed_empty(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
        mock_follow_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест получения пустой ленты."""
    # Настраиваем моки
    mock_follow_repo.get_following_ids.return_value = []  # Не подписан
    mock_tweet_repo.get_feed_for_user.return_value = []  # Нет твитов

    # Вызываем метод сервиса
    feed_result: TweetFeedResult = await tweet_service.get_tweet_feed(db=mock_db_session, current_user=test_user_obj)

    # Проверки
    assert isinstance(feed_result, TweetFeedResult)
    assert feed_result.result is True
    assert feed_result.tweets == []

    # Проверяем вызовы
    mock_follow_repo.get_following_ids.assert_awaited_once_with(mock_db_session,
                                                                follower_id=test_user_obj.id)
    # get_feed_for_user вызывается с ID только текущего пользователя
    expected_author_ids = [test_user_obj.id]  # Только ID текущего пользователя
    mock_tweet_repo.get_feed_for_user.assert_awaited_once_with(mock_db_session,
                                                               author_ids=expected_author_ids)
    # Нет твитов - нет вызовов
    mock_media_service.get_media_url.assert_not_called()
