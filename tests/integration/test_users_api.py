# tests/integration/test_users_api.py
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Follow

# Маркер для всех тестов в этом файле
pytestmark = pytest.mark.asyncio


# --- Тесты для GET /api_old/v1/users/me ---

async def test_get_me_success(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.get("/api_old/v1/users/me", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert data["user"]["id"] == test_user1.id
    assert data["user"]["name"] == test_user1.name
    assert "followers" in data["user"]
    assert "following" in data["user"]
    assert isinstance(data["user"]["followers"], list)
    assert isinstance(data["user"]["following"], list)


async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api_old/v1/users/me")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "unauthorized"


async def test_get_me_invalid_key(client: AsyncClient):
    headers = {"api-key": "invalidkey"}
    response = await client.get("/api_old/v1/users/me", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"


async def test_get_me_with_follows(
        client: AsyncClient,
        test_user1: User,
        test_user2: User,
        test_user3_no_tweets: User,  # User 3 follows User 1
        auth_headers_user1: dict,
        db_session: AsyncSession
):
    # User 1 follows User 2
    await db_session.execute(Follow.__table__.insert().values(follower_id=test_user1.id, following_id=test_user2.id))
    # User 3 follows User 1
    await db_session.execute(
        Follow.__table__.insert().values(follower_id=test_user3_no_tweets.id, following_id=test_user1.id))
    await db_session.commit()

    response = await client.get("/api_old/v1/users/me", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()["user"]

    assert len(data["following"]) == 1
    assert data["following"][0]["id"] == test_user2.id
    assert data["following"][0]["name"] == test_user2.name

    assert len(data["followers"]) == 1
    assert data["followers"][0]["id"] == test_user3_no_tweets.id
    assert data["followers"][0]["name"] == test_user3_no_tweets.name


# --- Тесты для GET /api_old/v1/users/{user_id} ---

async def test_get_user_profile_success(client: AsyncClient, test_user1: User, test_user2: User):
    # User 1 follows User 2 - setup in DB first
    # Note: This is better done via fixtures if used in multiple tests
    # async with TestingSessionLocal() as session: # Need a way to access db here or use fixture
    #     follow = Follow(follower_id=test_user1.id, following_id=test_user2.id)
    #     session.add(follow)
    #     await session.commit()

    response = await client.get(f"/api_old/v1/users/{test_user1.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert data["user"]["id"] == test_user1.id
    assert data["user"]["name"] == test_user1.name
    # Add checks for followers/following if data is set up


async def test_get_user_profile_not_found(client: AsyncClient):
    response = await client.get("/api_old/v1/users/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_get_user_profile_invalid_id_format(client: AsyncClient):
    response = await client.get("/api_old/v1/users/invalid")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # FastAPI handles path param type validation
