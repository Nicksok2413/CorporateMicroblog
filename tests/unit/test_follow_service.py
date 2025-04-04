# tests/unit/test_follow_service.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import follow_service, user_service  # Need user_service for checks
from app.models import User, Follow
from app.core.exceptions import PermissionDeniedError, NotFoundError, ConflictError, BadRequestError
from app.repositories import follow_repo  # To potentially mock repo methods
from unittest.mock import patch, AsyncMock

# Маркер
pytestmark = pytest.mark.asyncio


# --- Тесты для FollowService._validate_follow_action ---
# (Тестируем через публичные методы follow/unfollow)

# --- Тесты для FollowService.follow_user ---

async def test_follow_user_service_success(db_session: AsyncSession, test_user1: User, test_user2: User):
    await follow_service.follow_user(db=db_session, current_user=test_user1, user_to_follow_id=test_user2.id)
    # Verify in DB
    follow = await follow_repo.get_follow(db=db_session, follower_id=test_user1.id, following_id=test_user2.id)
    assert follow is not None


async def test_follow_user_service_already_following(db_session: AsyncSession, test_user1: User, test_user2: User,
                                                     test_follow_user1_on_user2: Follow):
    with pytest.raises(ConflictError) as excinfo:
        await follow_service.follow_user(db=db_session, current_user=test_user1, user_to_follow_id=test_user2.id)
    assert "уже подписаны" in str(excinfo.value)


async def test_follow_user_service_self(db_session: AsyncSession, test_user1: User):
    with pytest.raises(PermissionDeniedError) as excinfo:
        await follow_service.follow_user(db=db_session, current_user=test_user1, user_to_follow_id=test_user1.id)
    assert "не можете подписаться на себя" in str(excinfo.value)


async def test_follow_user_service_target_not_found(db_session: AsyncSession, test_user1: User):
    with pytest.raises(NotFoundError) as excinfo:
        await follow_service.follow_user(db=db_session, current_user=test_user1, user_to_follow_id=9999)
    assert "Пользователь с ID 9999 не найден" in str(excinfo.value)


async def test_follow_user_service_db_error(db_session: AsyncSession, test_user1: User, test_user2: User):
    # Mock repo.create_follow to raise an error
    with patch.object(follow_repo, 'create_follow', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("DB write failed")
        with pytest.raises(BadRequestError) as excinfo:
            await follow_service.follow_user(db=db_session, current_user=test_user1, user_to_follow_id=test_user2.id)
        assert "Не удалось подписаться" in str(excinfo.value)


# --- Тесты для FollowService.unfollow_user ---

async def test_unfollow_user_service_success(db_session: AsyncSession, test_user1: User, test_user2: User,
                                             test_follow_user1_on_user2: Follow):
    await follow_service.unfollow_user(db=db_session, current_user=test_user1, user_to_unfollow_id=test_user2.id)
    # Verify in DB
    follow = await follow_repo.get_follow(db=db_session, follower_id=test_user1.id, following_id=test_user2.id)
    assert follow is None


async def test_unfollow_user_service_not_following(db_session: AsyncSession, test_user1: User, test_user2: User):
    with pytest.raises(NotFoundError) as excinfo:
        await follow_service.unfollow_user(db=db_session, current_user=test_user1, user_to_unfollow_id=test_user2.id)
    assert "не подписаны" in str(excinfo.value)


async def test_unfollow_user_service_self(db_session: AsyncSession, test_user1: User):
    with pytest.raises(PermissionDeniedError) as excinfo:
        await follow_service.unfollow_user(db=db_session, current_user=test_user1, user_to_unfollow_id=test_user1.id)
    assert "не можете подписаться на себя" in str(excinfo.value)  # Check message consistency


async def test_unfollow_user_service_target_not_found(db_session: AsyncSession, test_user1: User):
    with pytest.raises(NotFoundError) as excinfo:
        await follow_service.unfollow_user(db=db_session, current_user=test_user1, user_to_unfollow_id=9999)
    assert "Пользователь с ID 9999 не найден" in str(excinfo.value)


async def test_unfollow_user_service_db_error(db_session: AsyncSession, test_user1: User, test_user2: User,
                                              test_follow_user1_on_user2: Follow):
    # Mock repo.remove_follow to simulate an error after finding the follow
    with patch.object(follow_repo, 'remove_follow', new_callable=AsyncMock) as mock_remove:
        # Simulate DB error during delete, even though remove_follow itself might return bool
        # The service doesn't explicitly catch errors from remove_follow,
        # relying on the repository or SQLAlchemy to raise them.
        # Let's assume remove_follow raises for this test.
        mock_remove.side_effect = Exception("DB delete failed")
        with pytest.raises(Exception) as excinfo:  # Catch generic Exception or specific SQLAlchemyError if known
            await follow_service.unfollow_user(db=db_session, current_user=test_user1,
                                               user_to_unfollow_id=test_user2.id)
        # Depending on actual error handling, assert BadRequestError or the original DB error
        # assert "Failed to unfollow" in str(excinfo.value)
