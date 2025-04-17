from unittest.mock import AsyncMock, MagicMock, call

import pytest
from sqlalchemy.exc import SQLAlchemyError  # Для имитации ошибок БД

from src.core.exceptions import (BadRequestError, ConflictError,
                                 NotFoundError, PermissionDeniedError)
from src.models import Like, Media, Tweet, User
from src.repositories import FollowRepository, MediaRepository, TweetRepository
from src.schemas.tweet import LikeInfo, TweetAuthor, TweetCreateRequest, TweetFeedResult, TweetInFeed
from src.services import MediaService, TweetService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---
# Фикстура для мока TweetRepository
@pytest.fixture
def mock_tweet_repo() -> MagicMock:
    repo = MagicMock(spec=TweetRepository)
    repo.create = AsyncMock()
    repo.get_with_attachments = AsyncMock()
    repo.get = AsyncMock()
    repo.delete = AsyncMock()
    repo.get_feed_for_user = AsyncMock()
    repo.model = Tweet
    return repo


# Фикстура для мока FollowRepository
@pytest.fixture
def mock_follow_repo() -> MagicMock:
    repo = MagicMock(spec=FollowRepository)
    repo.get_following_ids = AsyncMock()
    return repo


# Фикстура для мока MediaRepository
@pytest.fixture
def mock_media_repo() -> MagicMock:
    repo = MagicMock(spec=MediaRepository)
    repo.get = AsyncMock()
    repo.delete = AsyncMock()
    return repo


# Фикстура для мока MediaService
@pytest.fixture
def mock_media_service() -> MagicMock:
    service = MagicMock(spec=MediaService)
    service.get_media_url = MagicMock(side_effect=lambda m: f"/media/{m.file_path}")  # Простой мок URL
    service.delete_media_files = AsyncMock()
    return service


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
    tweet_data_req = TweetCreateRequest(tweet_data="Simple tweet")
    # Мок для repo.create не нужен, т.к. сервис создает объект Tweet сам
    # Мок для db.add нужен (неявно через сессию)
    # Мок для db.flush и db.commit

    # Вызов
    created_tweet = await tweet_service.create_tweet(
        db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_data_req
    )

    # Проверки
    assert created_tweet is not None
    assert created_tweet.content == tweet_data_req.tweet_data
    assert created_tweet.author_id == test_user_obj.id
    # Проверяем, что repo.create НЕ вызывался
    mock_tweet_repo.create.assert_not_awaited()
    # Проверяем, что repo.add вызывался (через сессию)
    # Проверить это сложно напрямую с моком сессии, проверяем flush и commit
    mock_db_session.add.assert_called_once()  # Проверяем что объект Tweet добавлен в сессию
    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()  # Проверяем refresh
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
    tweet_data_req = TweetCreateRequest(
        tweet_data="Tweet with media", tweet_media_ids=[media_id]
    )

    # Настройка моков
    # media_repo.get находит медиа, и оно не привязано (tweet_id is None)
    mock_media_repo.get.return_value = test_media_obj

    # Вызов
    created_tweet = await tweet_service.create_tweet(
        db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_data_req
    )

    # Проверки
    assert created_tweet is not None
    # Проверяем вызов media_repo.get
    mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    # Проверяем, что tweet_id у медиа объекта был обновлен
    assert test_media_obj.tweet_id == created_tweet.id
    # Проверяем flush и commit
    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


async def test_create_tweet_media_not_found(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_media_repo: MagicMock,
):
    """Тест создания твита, когда медиа не найден."""
    media_id = 999
    tweet_data_req = TweetCreateRequest(
        tweet_data="Tweet with bad media", tweet_media_ids=[media_id]
    )
    # Настройка мока - медиа не найдено
    mock_media_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_data_req
        )

    mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    mock_db_session.add.assert_not_called()  # Не должны дойти до создания твита
    mock_db_session.flush.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть откат


async def test_create_tweet_media_already_used(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_media_obj: Media,
        mock_media_repo: MagicMock,
):
    """Тест создания твита с медиа, которое уже привязано."""
    media_id = test_media_obj.id
    # Имитируем, что медиа уже привязано
    test_media_obj.tweet_id = 555
    tweet_data_req = TweetCreateRequest(
        tweet_data="Tweet reusing media", tweet_media_ids=[media_id]
    )
    mock_media_repo.get.return_value = test_media_obj

    with pytest.raises(ConflictError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_data_req
        )

    mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    mock_db_session.add.assert_not_called()
    mock_db_session.flush.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()


async def test_create_tweet_db_error_on_flush(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User
):
    """Тест ошибки БД при flush (например, при получении ID твита)."""
    tweet_data_req = TweetCreateRequest(tweet_data="Simple tweet")
    # Имитируем ошибку на flush
    mock_db_session.flush.side_effect = SQLAlchemyError("Flush error")

    with pytest.raises(BadRequestError):
        await tweet_service.create_tweet(
            db=mock_db_session, current_user=test_user_obj, tweet_data=tweet_data_req
        )

    mock_db_session.add.assert_called_once()
    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита не будет
    mock_db_session.rollback.assert_awaited_once()  # Должен быть откат


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

    # Вызов
    await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверки
    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=test_tweet_obj)
    mock_db_session.commit.assert_awaited_once()
    # Проверяем, что media_service.delete_media_files не вызывался
    mock_media_service.delete_media_files.assert_not_awaited()
    mock_db_session.rollback.assert_not_awaited()


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
    # Имитируем связь
    test_media_obj.tweet_id = tweet_id
    test_tweet_obj.attachments = [test_media_obj]

    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    mock_tweet_repo.delete.return_value = None
    mock_media_service.delete_media_files.return_value = None

    # Вызов
    await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    # Проверки
    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=test_tweet_obj)
    mock_db_session.commit.assert_awaited_once()
    # Проверяем вызов удаления файла
    expected_paths = [test_media_obj.file_path]
    mock_media_service.delete_media_files.assert_awaited_once_with(expected_paths)
    mock_db_session.rollback.assert_not_awaited()


async def test_delete_tweet_not_found(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест удаления несуществующего твита."""
    tweet_id = 999
    mock_tweet_repo.get_with_attachments.return_value = None

    with pytest.raises(NotFoundError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    mock_tweet_repo.delete.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_media_service.delete_media_files.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть откат (хотя ошибка до изменений)


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
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj

    with pytest.raises(PermissionDeniedError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=tweet_id)
    mock_tweet_repo.delete.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_media_service.delete_media_files.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть откат


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
    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    # Имитируем ошибку на commit
    mock_db_session.commit.side_effect = SQLAlchemyError("Commit failed")

    with pytest.raises(BadRequestError):
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    mock_tweet_repo.get_with_attachments.assert_awaited_once()
    mock_tweet_repo.delete.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.rollback.assert_awaited_once()  # Откат после неудачного коммита
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

    mock_tweet_repo.get_with_attachments.return_value = test_tweet_obj
    # Успешный коммит
    mock_db_session.commit.return_value = None
    # Ошибка при удалении файла
    file_error_message = "Cannot delete file"
    mock_media_service.delete_media_files.side_effect = Exception(file_error_message)

    with pytest.raises(BadRequestError) as exc_info:
        await tweet_service.delete_tweet(db=mock_db_session, current_user=test_user_obj, tweet_id=tweet_id)

    assert "ошибка при удалении его медиафайлов" in str(exc_info.value)

    # Проверяем, что коммит был
    mock_db_session.commit.assert_awaited_once()
    # Роллбэка не было, т.к. ошибка после коммита
    # mock_db_session.rollback.assert_awaited_once() # Это утверждение неверно здесь
    mock_db_session.rollback.assert_not_awaited()

    # Проверяем вызов удаления файлов
    expected_paths = [test_media_obj.file_path]
    mock_media_service.delete_media_files.assert_awaited_once_with(expected_paths)


# --- Тесты для get_tweet_feed ---

@pytest.fixture
def mock_tweet_with_relations() -> Tweet:
    """Фикстура для твита с имитацией связей."""
    author = User(id=5, name="Feed Author", api_key="key5")
    liker1 = User(id=6, name="Liker One", api_key="key6")
    liker2 = User(id=7, name="Liker Two", api_key="key7")
    media1 = Media(id=301, file_path="feed/img1.jpg", tweet_id=201)
    media2 = Media(id=302, file_path="feed/img2.png", tweet_id=201)

    tweet = Tweet(id=201, content="Tweet in feed", author_id=author.id)
    tweet.author = author  # Привязываем автора
    tweet.attachments = [media1, media2]  # Привязываем медиа
    # Привязываем лайки (создаем объекты Like с привязкой User)
    tweet.likes = [
        Like(user_id=liker1.id, tweet_id=tweet.id, user=liker1),
        Like(user_id=liker2.id, tweet_id=tweet.id, user=liker2),
    ]
    return tweet


async def test_get_tweet_feed_success(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_with_relations: Tweet,
        mock_tweet_repo: MagicMock,
        mock_follow_repo: MagicMock,
        mock_media_service: MagicMock,
):
    """Тест успешного получения и форматирования ленты."""
    # Настройка моков
    following_ids = [mock_tweet_with_relations.author_id, 8]  # ID автора + еще один
    mock_follow_repo.get_following_ids.return_value = following_ids
    # Репозиторий возвращает список с одним нашим тестовым твитом
    mock_tweet_repo.get_feed_for_user.return_value = [mock_tweet_with_relations]

    # Вызов
    feed_result: TweetFeedResult = await tweet_service.get_tweet_feed(db=mock_db_session, current_user=test_user_obj)

    # Проверки
    assert isinstance(feed_result, TweetFeedResult)
    assert feed_result.result is True
    assert len(feed_result.tweets) == 1

    # Проверяем вызовы репозиториев
    expected_author_ids = sorted(list(set(following_ids + [test_user_obj.id])))
    mock_follow_repo.get_following_ids.assert_awaited_once_with(db=mock_db_session,
                                                                               follower_id=test_user_obj.id)
    mock_tweet_repo.get_feed_for_user.assert_awaited_once()
    # Проверяем аргументы get_feed_for_user (сверяем списки ID авторов)
    call_args, call_kwargs = mock_tweet_repo.get_feed_for_user.call_args
    assert call_kwargs['author_ids'] == expected_author_ids

    # Проверяем форматирование одного твита
    formatted_tweet: TweetInFeed = feed_result.tweets[0]
    assert formatted_tweet.id == mock_tweet_with_relations.id
    assert formatted_tweet.content == mock_tweet_with_relations.content

    # Проверяем автора
    assert isinstance(formatted_tweet.author, TweetAuthor)
    assert formatted_tweet.author.id == mock_tweet_with_relations.author.id
    assert formatted_tweet.author.name == mock_tweet_with_relations.author.name

    # Проверяем лайки
    assert len(formatted_tweet.likes) == len(mock_tweet_with_relations.likes)
    assert isinstance(formatted_tweet.likes[0], LikeInfo)
    # Сверяем ID лайкнувших (используем множества для независимости от порядка)
    expected_liker_ids = {like.user.id for like in mock_tweet_with_relations.likes}
    actual_liker_ids = {like.id for like in formatted_tweet.likes}  # Используем id, а не user_id из-за alias
    assert actual_liker_ids == expected_liker_ids
    # Проверяем имена лайкнувших
    expected_liker_names = {like.user.name for like in mock_tweet_with_relations.likes}
    actual_liker_names = {like.name for like in formatted_tweet.likes}
    assert actual_liker_names == expected_liker_names

    # Проверяем медиа
    assert len(formatted_tweet.attachments) == len(mock_tweet_with_relations.attachments)
    # Проверяем вызов get_media_url для каждого медиа
    expected_calls = [
        call(mock_tweet_with_relations.attachments[0]),
        call(mock_tweet_with_relations.attachments[1]),
    ]
    mock_media_service.get_media_url.assert_has_calls(expected_calls, any_order=True)
    # Проверяем сами URL (используя простой мок get_media_url)
    assert formatted_tweet.attachments[0] == f"/media/{mock_tweet_with_relations.attachments[0].file_path}"
    assert formatted_tweet.attachments[1] == f"/media/{mock_tweet_with_relations.attachments[1].file_path}"


async def test_get_tweet_feed_empty(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_tweet_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест получения пустой ленты."""
    # Настройка моков
    mock_follow_repo.get_following_ids.return_value = []  # Не подписан
    mock_tweet_repo.get_feed_for_user.return_value = []  # Нет твитов

    # Вызов
    feed_result: TweetFeedResult = await tweet_service.get_tweet_feed(db=mock_db_session, current_user=test_user_obj)

    # Проверки
    assert feed_result.result is True
    assert feed_result.tweets == []

    # Проверяем вызовы (get_feed_for_user вызывается с ID только текущего пользователя)
    mock_follow_repo.get_following_ids.assert_awaited_once()
    mock_tweet_repo.get_feed_for_user.assert_awaited_once_with(mock_db_session,
                                                                              author_ids=[test_user_obj.id])
