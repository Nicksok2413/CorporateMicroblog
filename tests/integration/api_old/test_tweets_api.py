"""Интеграционные тесты для API эндпоинтов /tweets и лайков."""

import pytest
from httpx import AsyncClient
from fastapi import status

from app.models import Follow, Like, Tweet, User


# --- Тесты для POST /tweets (без изменений) ---
# ... (тесты test_create_tweet_success, test_create_tweet_unauthorized, ...)

# --- Тесты для GET /tweets (Дополненный) ---

@pytest.mark.asyncio
async def test_get_feed_includes_own_tweets(async_client: AsyncClient, test_user_alice: User,
                                            test_tweet_by_alice: Tweet):
    """Тест: лента включает собственные твиты."""
    headers = {"api-key": test_user_alice.api_key}
    response = await async_client.get("/api_old/v1/tweets", headers=headers)
    # ... (проверки как раньше) ...
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    assert len(json_response["tweets"]) >= 1
    found = any(tweet["id"] == test_tweet_by_alice.id for tweet in json_response["tweets"])
    assert found


@pytest.mark.asyncio
async def test_get_feed_includes_following_tweets(async_client: AsyncClient, test_user_alice: User,
                                                  test_tweet_by_bob: Tweet, alice_follows_bob: Follow):
    """Тест: лента включает твиты отслеживаемых пользователей."""
    headers = {"api-key": test_user_alice.api_key}
    response = await async_client.get("/api_old/v1/tweets", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    # Проверяем, что твит Боба есть в ленте Алисы
    found_bob_tweet = any(tweet["id"] == test_tweet_by_bob.id for tweet in json_response["tweets"])
    assert found_bob_tweet


# TODO: Добавить тест на сортировку по популярности (лайкам)
# TODO: Добавить тест на ленту с медиа

# --- Тесты для DELETE /tweets/{tweet_id} (без изменений) ---
# ... (тесты test_delete_tweet_success, test_delete_tweet_not_found, ...)

# --- Тесты для POST /tweets/{tweet_id}/likes ---

@pytest.mark.asyncio
async def test_like_tweet_success(async_client: AsyncClient, test_user_alice: User, test_tweet_by_bob: Tweet):
    """Тест успешного лайка твита."""
    headers = {"api-key": test_user_alice.api_key}
    tweet_id = test_tweet_by_bob.id

    response = await async_client.post(f"/api_old/v1/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True

    # Проверим, что лайк появился в ленте (или через профиль Боба)
    response_feed = await async_client.get("/api_old/v1/tweets", headers=headers)  # Лента Алисы
    feed = response_feed.json()["tweets"]
    bob_tweet_in_feed = next((t for t in feed if t["id"] == tweet_id), None)
    assert bob_tweet_in_feed is not None
    found_like = any(like["id"] == test_user_alice.id for like in bob_tweet_in_feed["likes"])
    assert found_like


@pytest.mark.asyncio
async def test_like_tweet_already_liked(async_client: AsyncClient, test_user_bob: User, test_tweet_by_alice: Tweet,
                                        bob_likes_alice_tweet: Like):
    """Тест повторного лайка (ошибка 409)."""
    headers = {"api-key": test_user_bob.api_key}  # Боб уже лайкнул
    tweet_id = test_tweet_by_alice.id

    response = await async_client.post(f"/api_old/v1/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "conflict_error"


@pytest.mark.asyncio
async def test_like_tweet_not_found(async_client: AsyncClient, test_user_alice: User):
    """Тест лайка несуществующего твита (ошибка 404)."""
    headers = {"api-key": test_user_alice.api_key}
    non_existent_id = 99999

    response = await async_client.post(f"/api_old/v1/tweets/{non_existent_id}/likes", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


# --- Тесты для DELETE /tweets/{tweet_id}/likes ---

@pytest.mark.asyncio
async def test_unlike_tweet_success(async_client: AsyncClient, test_user_bob: User, test_tweet_by_alice: Tweet,
                                    bob_likes_alice_tweet: Like):
    """Тест успешного снятия лайка."""
    headers = {"api-key": test_user_bob.api_key}  # Боб лайкнул
    tweet_id = test_tweet_by_alice.id

    response = await async_client.delete(f"/api_old/v1/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True


@pytest.mark.asyncio
async def test_unlike_tweet_not_liked(async_client: AsyncClient, test_user_alice: User, test_tweet_by_bob: Tweet):
    """Тест снятия лайка с твита, который не был лайкнут (ошибка 404)."""
    headers = {"api-key": test_user_alice.api_key}
    tweet_id = test_tweet_by_bob.id  # Алиса не лайкала твит Боба

    response = await async_client.delete(f"/api_old/v1/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


@pytest.mark.asyncio
async def test_unlike_tweet_not_found(async_client: AsyncClient, test_user_alice: User):
    """Тест снятия лайка с несуществующего твита (ошибка 404)."""
    headers = {"api-key": test_user_alice.api_key}
    non_existent_id = 99999

    response = await async_client.delete(f"/api_old/v1/tweets/{non_existent_id}/likes", headers=headers)

    # Ожидаем 404, так как remove_like не найдет лайк
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
