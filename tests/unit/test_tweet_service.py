from unittest.mock import AsyncMock, MagicMock, patch  # Используем AsyncMock для асинхронных методов

import pytest
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем сервисы и модели/схемы/исключения
from src.services.tweet_service import TweetService
from src.services.media_service import MediaService
from src.repositories import TweetRepository, FollowRepository, MediaRepository
from src.models import User, Tweet, Media
from src.schemas.tweet import TweetCreateRequest, TweetFeedResult, TweetInFeed, LikeInfo, TweetAuthor
from src.core.exceptions import NotFoundError, PermissionDeniedError, ConflictError, BadRequestError

pytestmark = pytest.mark.asyncio


# --- Фикстуры для моков ---
@pytest.fixture
def mock_db_session() -> MagicMock:
    """Мок сессии SQLAlchemy."""
    session = MagicMock(spec=AsyncSession)
    # Настраиваем асинхронные методы commit, rollback, refresh, flush
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_tweet_repo() -> MagicMock:
    repo = MagicMock(spec=TweetRepository)
    repo.get = AsyncMock()
    repo.get_with_attachments = AsyncMock()
    repo.get_feed_for_user = AsyncMock()
    repo.create = AsyncMock()  # Базовый create
    repo.add = AsyncMock()
    repo.delete = AsyncMock()
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
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_media_service() -> MagicMock:
    service = MagicMock(spec=MediaService)
    service.get_media_url = MagicMock(return_value="http://test/media/mock_path.jpg")  # Пример URL
    service.delete_media_files = AsyncMock()
    return service


@pytest.fixture
def tweet_service(
        mock_tweet_repo: TweetRepository,
        mock_follow_repo: FollowRepository,
        mock_media_repo: MediaRepository,
        mock_media_service: MediaService
) -> TweetService:
    """Экземпляр TweetService с замоканными зависимостями."""
    return TweetService(
        repo=mock_tweet_repo,
        follow_repo=mock_follow_repo,
        media_repo=mock_media_repo,
        media_service=mock_media_service
    )


# --- Тестовые данные ---
@pytest.fixture
def test_user() -> User:
    return User(id=1, name="Test User", api_key="test_key")


@pytest.fixture
def other_user() -> User:
    return User(id=2, name="Other User", api_key="other_key")


@pytest.fixture
def sample_tweet(test_user: User) -> Tweet:
    return Tweet(id=10, content="Sample tweet", author_id=test_user.id, author=test_user)


@pytest.fixture
def sample_media() -> Media:
    return Media(id=100, file_path="sample.jpg", tweet_id=None)  # Изначально не привязан


# === Тесты для create_tweet ===

async def test_create_tweet_simple_success(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        test_user: User
):
    tweet_data = TweetCreateRequest(tweet_data="Simple test tweet")
    # Мокаем возвращаемое значение add, т.к. оно используется для refresh
    mock_tweet_repo.add.return_value = None  # Не возвращает ничего специфичного

    # Ожидаем, что будет создан объект Tweet и добавлен в сессию
    created_tweet = await tweet_service.create_tweet(mock_db_session, test_user, tweet_data=tweet_data)

    # Проверяем вызовы моков
    mock_db_session.add.assert_called_once()
    added_obj = mock_db_session.add.call_args[0][0]  # Получаем объект, переданный в add
    assert isinstance(added_obj, Tweet)
    assert added_obj.content == tweet_data.tweet_data
    assert added_obj.author_id == test_user.id

    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(added_obj, attribute_names=['attachments'])
    assert created_tweet == added_obj  # Должен вернуть созданный объект


async def test_create_tweet_with_media_success(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        mock_media_repo: MagicMock,
        test_user: User,
        sample_media: Media  # Медиа без tweet_id
):
    media_id = sample_media.id
    tweet_data = TweetCreateRequest(tweet_data="Tweet with media", tweet_media_ids=[media_id])

    # Мокаем поиск медиа
    mock_media_repo.get.return_value = sample_media
    # Мокаем добавление твита
    mock_db_session.add.return_value = None  # Для refresh

    created_tweet = await tweet_service.create_tweet(mock_db_session, test_user, tweet_data=tweet_data)

    # Проверки
    mock_media_repo.get.assert_awaited_once_with(mock_db_session, obj_id=media_id)
    mock_db_session.add.assert_called_once()  # Только твит добавляется через add
    added_tweet = mock_db_session.add.call_args[0][0]

    assert isinstance(added_tweet, Tweet)
    assert added_tweet.content == tweet_data.tweet_data
    assert added_tweet.author_id == test_user.id
    # Проверяем, что у медиа установился tweet_id (хотя он модифицируется в сессии)
    assert sample_media.tweet_id == added_tweet.id  # ID должен быть назначен после flush

    mock_db_session.flush.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()
    assert created_tweet == added_tweet


async def test_create_tweet_media_not_found(
        tweet_service: TweetService, mock_db_session: MagicMock, mock_media_repo: MagicMock, test_user: User
):
    tweet_data = TweetCreateRequest(tweet_data="Tweet bad media", tweet_media_ids=[999])
    mock_media_repo.get.return_value = None  # Медиа не найдено

    with pytest.raises(NotFoundError):
        await tweet_service.create_tweet(mock_db_session, test_user, tweet_data=tweet_data)

    mock_db_session.commit.assert_not_awaited()  # Коммита не должно быть
    mock_db_session.rollback.assert_awaited_once()  # Роллбэк должен быть


async def test_create_tweet_media_already_used(
        tweet_service: TweetService, mock_db_session: MagicMock, mock_media_repo: MagicMock, test_user: User,
        sample_media: Media
):
    sample_media.tweet_id = 50  # Медиа уже привязано к другому твиту
    media_id = sample_media.id
    tweet_data = TweetCreateRequest(tweet_data="Tweet used media", tweet_media_ids=[media_id])
    mock_media_repo.get.return_value = sample_media

    with pytest.raises(ConflictError):
        await tweet_service.create_tweet(mock_db_session, test_user, tweet_data=tweet_data)

    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()


async def test_create_tweet_db_error(
        tweet_service: TweetService, mock_db_session: MagicMock, mock_tweet_repo: MagicMock, test_user: User
):
    tweet_data = TweetCreateRequest(tweet_data="DB error tweet")
    # Симулируем ошибку при коммите
    mock_db_session.commit.side_effect = SQLAlchemyError("DB connection failed")

    with pytest.raises(BadRequestError):
        await tweet_service.create_tweet(mock_db_session, test_user, tweet_data=tweet_data)

    mock_db_session.rollback.assert_awaited_once()  # Проверяем роллбэк


# === Тесты для delete_tweet ===

async def test_delete_tweet_success_no_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
        test_user: User,
        sample_tweet: Tweet  # Твит этого юзера
):
    sample_tweet.attachments = []  # Убедимся, что нет медиа
    mock_tweet_repo.get_with_attachments.return_value = sample_tweet

    await tweet_service.delete_tweet(mock_db_session, test_user, tweet_id=sample_tweet.id)

    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=sample_tweet.id)
    mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=sample_tweet)
    mock_db_session.commit.assert_awaited_once()
    mock_media_service.delete_media_files.assert_not_awaited()  # Не должно вызываться удаление файлов
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_delete_tweet_success_with_media(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
        test_user: User,
        sample_tweet: Tweet,
        sample_media: Media
):
    sample_media.tweet_id = sample_tweet.id  # Привязываем медиа
    sample_tweet.attachments = [sample_media]  # Устанавливаем связь
    mock_tweet_repo.get_with_attachments.return_value = sample_tweet

    await tweet_service.delete_tweet(mock_db_session, test_user, tweet_id=sample_tweet.id)

    mock_tweet_repo.get_with_attachments.assert_awaited_once_with(mock_db_session, obj_id=sample_tweet.id)
    mock_tweet_repo.delete.assert_awaited_once_with(mock_db_session, db_obj=sample_tweet)
    mock_db_session.commit.assert_awaited_once()
    # Проверяем, что удаление файлов вызвано с правильным путем
    mock_media_service.delete_media_files.assert_awaited_once_with([sample_media.file_path])
    mock_db_session.rollback.assert_not_awaited()


async def test_delete_tweet_not_found(
        tweet_service: TweetService, mock_db_session: MagicMock, mock_tweet_repo: MagicMock, test_user: User
):
    mock_tweet_repo.get_with_attachments.return_value = None  # Твит не найден

    with pytest.raises(NotFoundError):
        await tweet_service.delete_tweet(mock_db_session, test_user, tweet_id=999)

    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Роллбэк после ошибки поиска


async def test_delete_tweet_permission_denied(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        test_user: User,  # Юзер, который пытается удалить
        other_user: User,  # Автор твита
        sample_tweet: Tweet  # Твит, принадлежащий other_user
):
    sample_tweet.author_id = other_user.id  # Устанавливаем другого автора
    sample_tweet.author = other_user
    mock_tweet_repo.get_with_attachments.return_value = sample_tweet

    with pytest.raises(PermissionDeniedError):
        await tweet_service.delete_tweet(mock_db_session, test_user, tweet_id=sample_tweet.id)

    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()


async def test_delete_tweet_db_error_on_commit(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        test_user: User,
        sample_tweet: Tweet
):
    mock_tweet_repo.get_with_attachments.return_value = sample_tweet
    # Симулируем ошибку при коммите
    mock_db_session.commit.side_effect = SQLAlchemyError("Commit failed")

    with pytest.raises(BadRequestError) as exc_info:
        await tweet_service.delete_tweet(mock_db_session, test_user, tweet_id=sample_tweet.id)

    assert "Не удалось удалить твит из базы данных" in str(exc_info.value.detail)
    mock_tweet_repo.delete.assert_awaited_once()  # Удаление было вызвано
    mock_db_session.rollback.assert_awaited_once()  # Роллбэк был


async def test_delete_tweet_file_delete_error(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        mock_media_service: MagicMock,
        test_user: User,
        sample_tweet: Tweet,
        sample_media: Media
):
    sample_media.tweet_id = sample_tweet.id
    sample_tweet.attachments = [sample_media]
    mock_tweet_repo.get_with_attachments.return_value = sample_tweet
    # Симулируем ошибку при удалении файла ПОСЛЕ коммита
    mock_media_service.delete_media_files.side_effect = IOError("Cannot delete file")

    with pytest.raises(BadRequestError) as exc_info:
        await tweet_service.delete_tweet(mock_db_session, test_user, tweet_id=sample_tweet.id)

    assert "ошибка при удалении его медиафайлов" in str(exc_info.value.detail)
    mock_tweet_repo.delete.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()  # Коммит БД успешен
    mock_media_service.delete_media_files.assert_awaited_once()  # Попытка удаления была
    # mock_db_session.rollback.assert_not_awaited() # Отката БД после ошибки файла не должно быть


# === Тесты для get_tweet_feed === (простая проверка вызовов)

async def test_get_tweet_feed_logic(
        tweet_service: TweetService,
        mock_db_session: MagicMock,
        mock_tweet_repo: MagicMock,
        mock_follow_repo: MagicMock,
        mock_media_service: MagicMock,
        test_user: User,
        other_user: User
):
    # Мокируем данные
    following_ids = [other_user.id]
    mock_follow_repo.get_following_ids.return_value = following_ids

    # Мокируем твиты от репозитория (уже с нужными связями)
    tweet1 = Tweet(id=1, content="Tweet 1", author_id=test_user.id, author=test_user, attachments=[])
    media2 = Media(id=200, file_path="path2.jpg", tweet_id=2)
    tweet2 = Tweet(id=2, content="Tweet 2", author_id=other_user.id, author=other_user, attachments=[media2])
    mock_tweets_from_repo = [tweet2, tweet1]  # Пример сортировки
    mock_tweet_repo.get_feed_for_user.return_value = mock_tweets_from_repo

    # Мокируем URL
    mock_media_service.get_media_url.side_effect = lambda m: f"http://test/media/{m.file_path}"

    # Вызываем метод
    result: TweetFeedResult = await tweet_service.get_tweet_feed(mock_db_session, test_user)

    # Проверяем вызовы
    mock_follow_repo.get_following_ids.assert_awaited_once_with(mock_db_session, follower_id=test_user.id)
    # Проверяем, что в репозиторий передался ID текущего юзера и тех, на кого он подписан
    expected_author_ids = set(following_ids + [test_user.id])
    mock_tweet_repo.get_feed_for_user.assert_awaited_once()
    call_args, call_kwargs = mock_tweet_repo.get_feed_for_user.call_args
    assert call_kwargs['db'] == mock_db_session
    assert set(call_kwargs['author_ids']) == expected_author_ids

    # Проверяем результат
    assert result.result is True
    assert len(result.tweets) == 2

    # Проверяем форматирование одного твита
    formatted_tweet2 = next(t for t in result.tweets if t.id == 2)
    assert formatted_tweet2.content == "Tweet 2"
    assert formatted_tweet2.author.id == other_user.id
    assert formatted_tweet2.author.name == other_user.name
    assert len(formatted_tweet2.attachments) == 1
    assert formatted_tweet2.attachments[0] == "http://test/media/path2.jpg"
    assert formatted_tweet2.likes == []  # Лайков не мокировали

    formatted_tweet1 = next(t for t in result.tweets if t.id == 1)
    assert formatted_tweet1.author.id == test_user.id
    assert formatted_tweet1.attachments == []
