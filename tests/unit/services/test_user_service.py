# tests/unit/test_user_service.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import user_service, follow_service  # Импортируем оба сервиса
from app.models import User, Follow
from app.core.exceptions import NotFoundError
from app.schemas.user import BaseUser

# Маркер
pytestmark = pytest.mark.asyncio


# --- Тесты для UserService ---

async def test_get_user_by_id_success(db_session: AsyncSession, test_user1: User):
    user = await user_service.get_user_by_id(db_session, test_user1.id)
    assert user is not None
    assert user.id == test_user1.id
    assert user.name == test_user1.name


async def test_get_user_by_id_not_found(db_session: AsyncSession):
    user = await user_service.get_user_by_id(db_session, 999)
    assert user is None


async def test_get_user_by_api_key_success(db_session: AsyncSession, test_user1: User):
    user = await user_service.get_user_by_api_key(db_session, test_user1.api_key)
    assert user is not None
    assert user.id == test_user1.id


async def test_get_user_by_api_key_not_found(db_session: AsyncSession):
    user = await user_service.get_user_by_api_key(db_session, "nonexistentkey")
    assert user is None


async def test_get_user_or_404_success(db_session: AsyncSession, test_user1: User):
    user = await user_service._get_user_or_404(db_session, test_user1.id)
    assert user is not None
    assert user.id == test_user1.id


async def test_get_user_or_404_raises_not_found(db_session: AsyncSession):
    with pytest.raises(NotFoundError) as excinfo:
        await user_service._get_user_or_404(db_session, 999)
    assert "Пользователь с ID 999 не найден" in str(excinfo.value)


# --- Тесты для UserService.get_user_profile ---

async def test_get_user_profile_no_follows(db_session: AsyncSession, test_user1: User):
    profile = await user_service.get_user_profile(db_session, test_user1.id)
    assert profile.id == test_user1.id
    assert profile.name == test_user1.name
    assert profile.followers == []
    assert profile.following == []


async def test_get_user_profile_with_following(db_session: AsyncSession, test_user1: User, test_user2: User,
                                               test_follow_user1_on_user2: Follow):
    profile = await user_service.get_user_profile(db_session, test_user1.id)
    assert profile.id == test_user1.id
    assert len(profile.following) == 1
    assert isinstance(profile.following[0], BaseUser)
    assert profile.following[0].id == test_user2.id
    assert profile.following[0].name == test_user2.name
    assert profile.followers == []


async def test_get_user_profile_with_followers(db_session: AsyncSession, test_user1: User, test_user2: User,
                                               test_follow_user2_on_user1: Follow):  # Need this fixture
    # Fixture 'test_follow_user2_on_user1' follows user1 from user2
    profile = await user_service.get_user_profile(db_session, test_user1.id)
    assert profile.id == test_user1.id
    assert profile.following == []
    assert len(profile.followers) == 1
    assert isinstance(profile.followers[0], BaseUser)
    assert profile.followers[0].id == test_user2.id
    assert profile.followers[0].name == test_user2.name


async def test_get_user_profile_with_both(
        db_session: AsyncSession,
        test_user1: User,
        test_user2: User,
        test_user3_no_tweets: User,
        test_follow_user1_on_user2: Follow,  # user1 follows user2
        test_follow_user3_on_user1: Follow,  # user3 follows user1 - need fixture
):
    profile = await user_service.get_user_profile(db_session, test_user1.id)
    assert profile.id == test_user1.id

    assert len(profile.following) == 1
    assert profile.following[0].id == test_user2.id

    assert len(profile.followers) == 1
    assert profile.followers[0].id == test_user3_no_tweets.id


async def test_get_user_profile_raises_not_found(db_session: AsyncSession):
    with pytest.raises(NotFoundError):
        await user_service.get_user_profile(db_session, 999)
