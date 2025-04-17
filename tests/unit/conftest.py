from unittest.mock import MagicMock, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Tweet, Media, Like, Follow


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


@pytest.fixture
def mock_current_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = 1
    return user
