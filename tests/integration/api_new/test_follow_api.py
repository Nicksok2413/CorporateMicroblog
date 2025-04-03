# tests/integration/test_follow_api.py
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Follow

# Маркер для всех тестов в этом файле
pytestmark = pytest.mark.asyncio


# --- Тесты для POST /api/v1/users/{user_id}/follow ---

async def test_follow_user_success(client: AsyncClient, test_user1: User, test_user2: User, auth_headers_user1: dict,
                                   db_session: AsyncSession):
    response = await client.post(f"/api/v1/users/{test_user2.id}/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True

    # Verify follow exists in DB
    follow = await db_session.get(Follow, (test_user1.id, test_user2.id))
    assert follow is not None
    assert follow.follower_id == test_user1.id
    assert follow.following_id == test_user2.id


async def test_follow_user_already_following(client: AsyncClient, test_user1: User, test_user2: User,
                                             test_follow_user1_on_user2: Follow, auth_headers_user1: dict):
    # User 1 already follows User 2 via fixture
    response = await client.post(f"/api/v1/users/{test_user2.id}/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "conflict_error"


async def test_follow_user_self(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.post(f"/api/v1/users/{test_user1.id}/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # Or 400 depending on where the check is
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"  # Based on FollowService exception
    assert "не можете подписаться на себя" in data["error_message"]


async def test_follow_user_not_found(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.post("/api/v1/users/9999/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_follow_user_unauthorized(client: AsyncClient, test_user2: User):
    response = await client.post(f"/api/v1/users/{test_user2.id}/follow")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_follow_user_invalid_key(client: AsyncClient, test_user2: User):
    headers = {"api-key": "invalidkey"}
    response = await client.post(f"/api/v1/users/{test_user2.id}/follow", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Тесты для DELETE /api/v1/users/{user_id}/follow ---

async def test_unfollow_user_success(client: AsyncClient, test_user1: User, test_user2: User,
                                     test_follow_user1_on_user2: Follow, auth_headers_user1: dict,
                                     db_session: AsyncSession):
    response = await client.delete(f"/api/v1/users/{test_user2.id}/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True

    # Verify follow is deleted from DB
    follow = await db_session.get(Follow, (test_user1.id, test_user2.id))
    assert follow is None


async def test_unfollow_user_not_following(client: AsyncClient, test_user1: User, test_user2: User,
                                           auth_headers_user1: dict):
    # User 1 tries to unfollow User 2, whom they are not following
    response = await client.delete(f"/api/v1/users/{test_user2.id}/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"
    assert "не подписаны" in data["error_message"]


async def test_unfollow_user_self(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.delete(f"/api/v1/users/{test_user1.id}/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # Or 400
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"


async def test_unfollow_user_not_found(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.delete("/api/v1/users/9999/follow", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_unfollow_user_unauthorized(client: AsyncClient, test_user2: User):
    response = await client.delete(f"/api/v1/users/{test_user2.id}/follow")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unfollow_user_invalid_key(client: AsyncClient, test_user2: User):
    headers = {"api-key": "invalidkey"}
    response = await client.delete(f"/api/v1/users/{test_user2.id}/follow", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
