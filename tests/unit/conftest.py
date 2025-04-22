from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Media, Tweet, User
from src.repositories import (
    FollowRepository,
    LikeRepository,
    MediaRepository,
    TweetRepository,
    UserRepository,
)
from src.services import (
    FollowService,
    LikeService,
    MediaService,
    TweetService,
    UserService,
)


# Мок сессии БД
@pytest.fixture
def mock_db_session() -> MagicMock:
    """Фикстура для мока сессии SQLAlchemy."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    # Имитируем асинхронный контекстный менеджер (для `async with db.session()`)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


# --- Фикстуры для моков репозиториев ---


# Фикстура для мока FollowRepository
@pytest.fixture
def mock_follow_repo() -> MagicMock:
    repo = MagicMock(spec=FollowRepository)
    repo.get_follow = AsyncMock()
    repo.add_follow = AsyncMock()
    repo.delete_follow = AsyncMock()
    repo.get_following_with_users = AsyncMock()
    repo.get_followers_with_users = AsyncMock()
    repo.get_following_ids = AsyncMock()
    return repo


# Фикстура для мока LikeRepository
@pytest.fixture
def mock_like_repo() -> MagicMock:
    repo = MagicMock(spec=LikeRepository)
    repo.get_like = AsyncMock()
    repo.add_like = AsyncMock()
    repo.delete_like = AsyncMock()
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


# Фикстура для мока FollowService
@pytest.fixture
def mock_follow_service() -> MagicMock:
    service = MagicMock(spec=FollowService)
    service.follow_user = AsyncMock()
    service.unfollow_user = AsyncMock()
    return service


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
    service.get_media_url = MagicMock(side_effect=lambda m: f"/media/{m.file_path}")
    return service


# Фикстура для мока TweetService
@pytest.fixture
def mock_tweet_service() -> MagicMock:
    service = MagicMock(spec=TweetService)
    service.get_tweet_feed = AsyncMock()
    service.create_tweet = AsyncMock()
    service.delete_tweet = AsyncMock()
    return service


# Фикстура для мока UserService
@pytest.fixture
def mock_user_service() -> MagicMock:
    service = MagicMock(spec=UserService)
    service.get_user_profile = AsyncMock()
    return service
