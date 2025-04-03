# tests/integration/test_likes_api.py
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Tweet, Like

# Маркер для всех тестов в этом файле
pytestmark = pytest.mark.asyncio


# --- Тесты для POST /api/v1/tweets/{tweet_id}/likes ---

async def test_like_tweet_success(client: AsyncClient, test_user1: User, test_tweet_user2: Tweet,
                                  auth_headers_user1: dict, db_session: AsyncSession):
    response = await client.post(f"/api/v1/tweets/{test_tweet_user2.id}/likes", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True

    # Verify like exists in DB
    like = await db_session.get(Like, (test_user1.id, test_tweet_user2.id))
    assert like is not None
    assert like.user_id == test_user1.id
    assert like.tweet_id == test_tweet_user2.id


async def test_like_tweet_already_liked(client: AsyncClient, test_user1: User, test_tweet_user2: Tweet,
                                        auth_headers_user1: dict, db_session: AsyncSession):
    # Like it once first
    await client.post(f"/api/v1/tweets/{test_tweet_user2.id}/likes", headers=auth_headers_user1)
    # Try to like again
    response = await client.post(f"/api/v1/tweets/{test_tweet_user2.id}/likes", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "conflict_error"


async def test_like_tweet_not_found(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.post("/api/v1/tweets/9999/likes", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_like_tweet_unauthorized(client: AsyncClient, test_tweet_user1: Tweet):
    response = await client.post(f"/api/v1/tweets/{test_tweet_user1.id}/likes")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_like_tweet_invalid_key(client: AsyncClient, test_tweet_user1: Tweet):
    headers = {"api-key": "invalidkey"}
    response = await client.post(f"/api/v1/tweets/{test_tweet_user1.id}/likes", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Тесты для DELETE /api/v1/tweets/{tweet_id}/likes ---

async def test_unlike_tweet_success(client: AsyncClient, test_user2: User, test_tweet_user1: Tweet,
                                    test_like_user2_on_tweet1: Like, auth_headers_user2: dict,
                                    db_session: AsyncSession):
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}/likes", headers=auth_headers_user2)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True

    # Verify like is deleted from DB
    like = await db_session.get(Like, (test_user2.id, test_tweet_user1.id))
    assert like is None


async def test_unlike_tweet_not_liked(client: AsyncClient, test_user1: User, test_tweet_user2: Tweet,
                                      auth_headers_user1: dict):
    # User 1 tries to unlike User 2's tweet which they haven't liked
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user2.id}/likes", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"
    assert "Лайк не найден" in data["error_message"]


async def test_unlike_tweet_not_found(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    # Try to unlike a non-existent tweet
    response = await client.delete("/api/v1/tweets/9999/likes", headers=auth_headers_user1)
    # This will likely also result in a 404 because the like won't exist
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_unlike_tweet_unauthorized(client: AsyncClient, test_tweet_user1: Tweet):
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}/likes")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unlike_tweet_invalid_key(client: AsyncClient, test_tweet_user1: Tweet):
    headers = {"api-key": "invalidkey"}
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}/likes", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
