# tests/integration/test_tweets_api.py
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Follow, Like, Media, Tweet, User

# Маркер для всех тестов в этом файле
pytestmark = pytest.mark.asyncio


# --- Тесты для POST /api/v1/tweets ---

async def test_create_tweet_success_text_only(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    tweet_data = {"tweet_data": "A simple text tweet"}
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True
    assert "tweet_id" in data
    assert isinstance(data["tweet_id"], int)


async def test_create_tweet_success_with_media(client: AsyncClient, test_user1: User, test_media: Media,
                                               auth_headers_user1: dict):
    tweet_data = {
        "tweet_data": "Tweet with media",
        "tweet_media_ids": [test_media.id]
    }
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True
    assert isinstance(data["tweet_id"], int)
    # TODO: Verify association in DB if needed


async def test_create_tweet_success_with_multiple_media(client: AsyncClient, test_user1: User,
                                                        test_media_list: list[Media], auth_headers_user1: dict):
    tweet_data = {
        "tweet_data": "Tweet with multiple media",
        "tweet_media_ids": [m.id for m in test_media_list]
    }
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True
    assert isinstance(data["tweet_id"], int)


async def test_create_tweet_invalid_media_id(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    tweet_data = {"tweet_data": "Tweet with invalid media", "tweet_media_ids": [9999]}
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"
    assert "Медиафайл с ID 9999 не найден" in data["error_message"]


async def test_create_tweet_validation_too_long(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    long_text = "a" * 281
    tweet_data = {"tweet_data": long_text}
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Check specific validation error message if needed


async def test_create_tweet_validation_missing_data(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    tweet_data = {}  # Missing tweet_data
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_tweet_unauthorized(client: AsyncClient):
    tweet_data = {"tweet_data": "Unauthorized tweet"}
    response = await client.post("/api/v1/tweets", json=tweet_data)  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_create_tweet_invalid_key(client: AsyncClient):
    tweet_data = {"tweet_data": "Invalid key tweet"}
    headers = {"api-key": "invalidkey"}
    response = await client.post("/api/v1/tweets", json=tweet_data, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Тесты для GET /api/v1/tweets ---

async def test_get_feed_success_empty(client: AsyncClient, test_user3_no_tweets: User):
    # User 3 has no tweets and follows no one
    headers = {"api-key": test_user3_no_tweets.api_key}
    response = await client.get("/api/v1/tweets", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert data["tweets"] == []


async def test_get_feed_success_own_tweets(client: AsyncClient, test_user1: User, test_tweet_user1: Tweet,
                                           auth_headers_user1: dict):
    response = await client.get("/api/v1/tweets", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert len(data["tweets"]) == 1
    assert data["tweets"][0]["id"] == test_tweet_user1.id
    assert data["tweets"][0]["content"] == test_tweet_user1.content
    assert data["tweets"][0]["author"]["id"] == test_user1.id
    assert data["tweets"][0]["author"]["name"] == test_user1.name
    assert data["tweets"][0]["likes"] == []
    assert data["tweets"][0]["attachments"] == []  # Assuming no attachments in fixture


async def test_get_feed_success_following(
        client: AsyncClient,
        test_user1: User,
        test_user2: User,
        test_tweet_user1: Tweet,
        test_tweet_user2: Tweet,
        test_follow_user1_on_user2: Follow,
        auth_headers_user1: dict
):
    response = await client.get("/api/v1/tweets", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert len(data["tweets"]) == 2  # Own + Followed

    # Check sorting (most recent first by default if no likes)
    # Assuming test_tweet_user2 is created after test_tweet_user1 in fixtures
    assert data["tweets"][0]["id"] == test_tweet_user2.id
    assert data["tweets"][1]["id"] == test_tweet_user1.id

    # Verify structure of one tweet
    tweet_in_feed = next(t for t in data["tweets"] if t["id"] == test_tweet_user2.id)
    assert tweet_in_feed["content"] == test_tweet_user2.content
    assert tweet_in_feed["author"]["id"] == test_user2.id
    assert tweet_in_feed["likes"] == []
    assert tweet_in_feed["attachments"] == []


async def test_get_feed_check_attachments_and_likes(
        client: AsyncClient,
        test_user1: User,
        test_user2: User,
        test_tweet_user1_with_media: Tweet,  # User 1's tweet with media
        test_like_user2_on_tweet1: Like,  # User 2 liked User 1's tweet
        auth_headers_user1: dict,
        settings  # Need settings for media URL prefix
):
    response = await client.get("/api/v1/tweets", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert len(data["tweets"]) == 1
    tweet_in_feed = data["tweets"][0]

    assert tweet_in_feed["id"] == test_tweet_user1_with_media.id

    # Check attachments (URLs)
    assert len(tweet_in_feed["attachments"]) == 2
    assert f"{settings.MEDIA_URL_PREFIX}/image1.png" in tweet_in_feed["attachments"]
    assert f"{settings.MEDIA_URL_PREFIX}/image2.gif" in tweet_in_feed["attachments"]

    # Check likes
    assert len(tweet_in_feed["likes"]) == 1
    assert tweet_in_feed["likes"][0]["user_id"] == test_user2.id  # Assuming LikeInfo schema uses user_id
    assert tweet_in_feed["likes"][0]["name"] == test_user2.name


async def test_get_feed_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/tweets")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_feed_invalid_key(client: AsyncClient):
    headers = {"api-key": "invalidkey"}
    response = await client.get("/api/v1/tweets", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Тесты для DELETE /api/v1/tweets/{tweet_id} ---

async def test_delete_tweet_success(client: AsyncClient, test_user1: User, test_tweet_user1: Tweet,
                                    auth_headers_user1: dict, db_session: AsyncSession):
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True

    # Verify tweet is deleted from DB
    tweet = await db_session.get(Tweet, test_tweet_user1.id)
    assert tweet is None


async def test_delete_tweet_forbidden(client: AsyncClient, test_user2: User, test_tweet_user1: Tweet,
                                      auth_headers_user2: dict):
    # User 2 tries to delete User 1's tweet
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}", headers=auth_headers_user2)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"


async def test_delete_tweet_not_found(client: AsyncClient, test_user1: User, auth_headers_user1: dict):
    response = await client.delete("/api/v1/tweets/9999", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_delete_tweet_unauthorized(client: AsyncClient, test_tweet_user1: Tweet):
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_delete_tweet_invalid_key(client: AsyncClient, test_tweet_user1: Tweet):
    headers = {"api-key": "invalidkey"}
    response = await client.delete(f"/api/v1/tweets/{test_tweet_user1.id}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
