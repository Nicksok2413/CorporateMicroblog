# tests/unit/test_tweet_service.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import tweet_service
from app.models import User, Tweet, Media, Follow, Like
from app.core.exceptions import PermissionDeniedError, NotFoundError, ConflictError
from app.schemas.tweet import TweetCreateRequest

# Маркер
pytestmark = pytest.mark.asyncio


# --- Тесты для tweet_service.delete_tweet ---

async def test_delete_tweet_service_forbidden(db_session: AsyncSession, test_user1: User, test_user2: User,
                                              test_tweet_user1: Tweet):
    # User 2 tries to delete User 1's tweet via service
    with pytest.raises(PermissionDeniedError) as excinfo:
        await tweet_service.delete_tweet(db=db_session, tweet_id=test_tweet_user1.id, current_user=test_user2)
    assert "не можете удалить этот твит" in str(excinfo.value)


async def test_delete_tweet_service_not_found(db_session: AsyncSession, test_user1: User):
    with pytest.raises(NotFoundError):
        await tweet_service.delete_tweet(db=db_session, tweet_id=9999, current_user=test_user1)


# --- Тесты для tweet_service.like_tweet ---

async def test_like_tweet_service_already_liked(db_session: AsyncSession, test_user1: User, test_tweet_user2: Tweet,
                                                test_like_user1_on_tweet2: Like):  # Need like fixture
    # Assume test_like_user1_on_tweet2 creates a like from user1 on tweet2
    with pytest.raises(ConflictError) as excinfo:
        await tweet_service.like_tweet(db=db_session, tweet_id=test_tweet_user2.id, current_user=test_user1)
    assert "уже лайкнули" in str(excinfo.value)


# --- Тесты для tweet_service.get_tweet_feed ---
# (Более сложные, т.к. требуют настройки подписок и лайков)

async def test_get_feed_service_data_formatting(
        db_session: AsyncSession,
        test_user1: User,
        test_user2: User,
        test_tweet_user1_with_media: Tweet,
        test_like_user2_on_tweet1: Like,
        settings  # Need settings for media URL
):
    # User1 feed should contain their tweet with media and like from user2
    feed_result = await tweet_service.get_tweet_feed(db=db_session, current_user=test_user1)
    assert len(feed_result.tweets) == 1
    tweet_dto = feed_result.tweets[0]

    assert tweet_dto.id == test_tweet_user1_with_media.id
    assert tweet_dto.content == test_tweet_user1_with_media.content
    assert tweet_dto.author.id == test_user1.id
    assert tweet_dto.author.name == test_user1.name
    assert len(tweet_dto.attachments) == 2  # From fixture test_tweet_user1_with_media
    assert f"{settings.MEDIA_URL_PREFIX}/image1.png" in tweet_dto.attachments
    assert len(tweet_dto.likes) == 1
    assert tweet_dto.likes[0].user_id == test_user2.id  # Assuming LikeInfo schema uses user_id
    assert tweet_dto.likes[0].name == test_user2.name

# Добавьте больше юнит-тестов для других сервисов и сложных методов
