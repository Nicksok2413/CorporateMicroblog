from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Follow, Like, Media, Tweet, User
from src.repositories import (FollowRepository, MediaRepository,
                              TweetRepository, UserRepository)
from src.services import LikeService, MediaService, TweetService


# --- Мок сессии БД ---
@pytest.fixture
def mock_db_session() -> MagicMock:
    """Фикстура для мока сессии SQLAlchemy."""
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    return session


# --- Фикстуры для базовых объектов моделей ---

@pytest.fixture
def test_user_obj() -> User:
    return User(id=1, name="Test User", api_key="testkey1")


@pytest.fixture
def test_alice_obj() -> User:
    return User(id=2, name="Test Alice", api_key="testkey2")


@pytest.fixture
def test_bob_obj() -> User:
    return User(id=3, name="Test Bob", api_key="testkey3")


@pytest.fixture
def test_tweet_obj() -> Tweet:
    # Создаем с минимально необходимыми полями для тестов
    tweet = Tweet(id=101, content="Test Tweet Content", author_id=1)
    # Имитируем пустые связи, если тест не мокирует их загрузку
    tweet.attachments = []
    tweet.likes = []
    return tweet


@pytest.fixture
def test_media_obj() -> Media:
    # tweet_id=None по умолчанию, пока не привязан
    return Media(id=201, file_path="test/path/image.jpg", tweet_id=None)


@pytest.fixture
def test_like_obj() -> Like:
    return Like(user_id=1, tweet_id=101)


@pytest.fixture
def test_follow_obj() -> Follow:
    return Follow(follower_id=1, following_id=2)


# --- Фикстуры для моков репозиториев ---

# Фикстура для мока FollowRepository
@pytest.fixture
def mock_follow_repo() -> MagicMock:
    repo = MagicMock(spec=FollowRepository)
    repo.get_following_with_users = AsyncMock()
    repo.get_followers_with_users = AsyncMock()
    repo.get_following_ids = AsyncMock()
    return repo


# Фикстура для мока MediaRepository
@pytest.fixture
def mock_media_repo() -> MagicMock:
    repo = MagicMock(spec=MediaRepository)
    repo.create = AsyncMock()
    repo.delete = AsyncMock()
    repo.model = Media
    return repo


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


# Фикстура для мока UserRepository
@pytest.fixture
def mock_user_repo() -> MagicMock:
    repo = MagicMock(spec=UserRepository)
    repo.get_by_api_key = AsyncMock()
    repo.get = AsyncMock()
    repo.model = User
    return repo


# --- Фикстуры для моков сервисов ---

# Фикстура для мока LikeService
@pytest.fixture
def mock_like_service() -> MagicMock:
    service = MagicMock(spec=LikeService)
    service.like_tweet = AsyncMock()
    service.unlike_tweet = AsyncMock()
    return service


# Фикстура для мока MediaService
@pytest.fixture
def mock_media_service() -> MagicMock:
    service = MagicMock(spec=MediaService)
    service.save_media_file = AsyncMock()
    service.delete_media_files = AsyncMock()
    service.get_media_url = MagicMock(side_effect=lambda m: f"/media/{m.file_path}")  # Простой мок URL
    return service


# Фикстура для мока TweetService
@pytest.fixture
def mock_tweet_service() -> MagicMock:
    service = MagicMock(spec=TweetService)
    service.get_tweet_feed = AsyncMock()
    service.create_tweet = AsyncMock()
    service.delete_tweet = AsyncMock()
    return service
