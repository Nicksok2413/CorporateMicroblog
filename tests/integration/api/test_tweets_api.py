"""Интеграционные тесты для API эндпоинтов /tweets."""

import pytest
from httpx import AsyncClient
from fastapi import status

# Импортируем модели и схемы для проверок
from app.models import User, Tweet
from app.schemas import TweetFeedResult, TweetCreateResult, TweetActionResult


# --- Тесты для POST /tweets ---

@pytest.mark.asyncio
async def test_create_tweet_success(async_client: AsyncClient, test_user_alice: User):
    """Тест успешного создания твита."""
    tweet_data = {"tweet_data": "My first API test tweet!"}
    headers = {"api-key": test_user_alice.api_key}

    response = await async_client.post("/api/v1/tweets", json=tweet_data, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    # Проверяем базовую структуру ответа
    assert json_response["result"] is True
    assert "tweet_id" in json_response
    assert isinstance(json_response["tweet_id"], int)
    # Можно добавить проверку в БД, если нужно (но это уже глубже)


@pytest.mark.asyncio
async def test_create_tweet_unauthorized(async_client: AsyncClient):
    """Тест создания твита без API ключа (ошибка 401)."""
    tweet_data = {"tweet_data": "This should fail"}

    response = await async_client.post("/api/v1/tweets", json=tweet_data)  # Без заголовка

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "AuthenticationRequiredError"  # или как определено в обработчике


@pytest.mark.asyncio
async def test_create_tweet_invalid_key(async_client: AsyncClient):
    """Тест создания твита с неверным API ключом (ошибка 403)."""
    tweet_data = {"tweet_data": "This should also fail"}
    headers = {"api-key": "invalid-api-key"}

    response = await async_client.post("/api/v1/tweets", json=tweet_data, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "permission_denied"  # или как определено в обработчике


@pytest.mark.asyncio
async def test_create_tweet_validation_error(async_client: AsyncClient, test_user_alice: User):
    """Тест создания твита с невалидными данными (ошибка 422)."""
    # Слишком длинный твит
    long_content = "a" * 300
    tweet_data = {"tweet_data": long_content}
    headers = {"api-key": test_user_alice.api_key}

    response = await async_client.post("/api/v1/tweets", json=tweet_data, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "Validation Error"
    assert "tweet_data" in json_response["error_message"]  # Проверяем, что ошибка связана с полем


# TODO: Добавить тесты для создания твита с медиа (потребует фикстуры для медиа)

# --- Тесты для GET /tweets ---

@pytest.mark.asyncio
async def test_get_feed_success(async_client: AsyncClient, test_user_alice: User, test_tweet_by_alice: Tweet):
    """Тест успешного получения ленты (пока только свои твиты)."""
    headers = {"api-key": test_user_alice.api_key}
    response = await async_client.get("/api/v1/tweets", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    # Проверяем структуру ответа
    assert json_response["result"] is True
    assert "tweets" in json_response
    assert isinstance(json_response["tweets"], list)

    # Проверяем, что наш тестовый твит есть в ленте
    assert len(json_response["tweets"]) >= 1
    found = any(tweet["id"] == test_tweet_by_alice.id for tweet in json_response["tweets"])
    assert found

    # Проверяем структуру одного твита в ленте
    tweet_in_feed = json_response["tweets"][0]
    assert "id" in tweet_in_feed
    assert "content" in tweet_in_feed
    assert "attachments" in tweet_in_feed
    assert "author" in tweet_in_feed
    assert "id" in tweet_in_feed["author"]
    assert "name" in tweet_in_feed["author"]
    assert "likes" in tweet_in_feed
    assert isinstance(tweet_in_feed["likes"], list)


# TODO: Добавить тесты для ленты с подписками
# TODO: Добавить тесты для ленты с лайками
# TODO: Добавить тесты для ленты с медиа

# --- Тесты для DELETE /tweets/{tweet_id} ---

@pytest.mark.asyncio
async def test_delete_tweet_success(async_client: AsyncClient, test_user_alice: User, test_tweet_by_alice: Tweet):
    """Тест успешного удаления своего твита."""
    headers = {"api-key": test_user_alice.api_key}
    tweet_id = test_tweet_by_alice.id

    response = await async_client.delete(f"/api/v1/tweets/{tweet_id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем, что твит действительно удален (опционально)
    response_get = await async_client.get(f"/api/v1/tweets", headers=headers)  # Получаем ленту снова
    feed_after_delete = response_get.json()
    found_after_delete = any(tweet["id"] == tweet_id for tweet in feed_after_delete["tweets"])
    assert not found_after_delete


@pytest.mark.asyncio
async def test_delete_tweet_not_found(async_client: AsyncClient, test_user_alice: User):
    """Тест удаления несуществующего твита (ошибка 404)."""
    headers = {"api-key": test_user_alice.api_key}
    non_existent_id = 99999

    response = await async_client.delete(f"/api/v1/tweets/{non_existent_id}", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


@pytest.mark.asyncio
async def test_delete_tweet_forbidden(async_client: AsyncClient, test_user_bob: User, test_tweet_by_alice: Tweet):
    """Тест попытки удаления чужого твита (ошибка 403)."""
    headers = {"api-key": test_user_bob.api_key}  # Ключ Боба
    tweet_id = test_tweet_by_alice.id  # Твит Алисы

    response = await async_client.delete(f"/api/v1/tweets/{tweet_id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "permission_denied"

# TODO: Добавить тесты для эндпоинтов лайков (/tweets/{id}/likes)
# TODO: Добавить тесты для эндпоинтов подписок (/users/{id}/follow)
# TODO: Добавить тесты для эндпоинтов профилей (/users/me, /users/{id})
# TODO: Добавить тесты для загрузки медиа (/medias)
