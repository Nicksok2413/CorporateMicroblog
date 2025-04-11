import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Follow, Like, Media, User, Tweet  # Импортируем модели для type hinting и проверок
from src.schemas.tweet import TweetCreateResult, TweetActionResult, TweetFeedResult, TweetInFeed  # Схемы для проверок

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тесты создания твитов ---

async def test_create_tweet_success(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,  # Фикстура пользователя нужна для проверок
):
    """Тест успешного создания твита."""
    tweet_data = {"tweet_data": "My first test tweet!"}
    response = await async_client.post("/api/tweets", json=tweet_data, headers=nick_headers)

    assert response.status_code == status.HTTP_201_CREATED
    result = TweetCreateResult(**response.json())
    assert result.result is True
    assert isinstance(result.tweet_id, int)
    # Дополнительная проверка: найти твит в БД (опционально, но полезно)
    # Нужна фикстура db_session для прямого доступа к БД в тесте
    # tweet_db = await db_session.get(Tweet, result.tweet_id)
    # assert tweet_db is not None
    # assert tweet_db.content == tweet_data["tweet_data"]
    # assert tweet_db.author_id == test_user_nick.id


async def test_create_tweet_with_media_success(
        async_client: AsyncClient,
        nick_headers: dict,
        test_media: Media,  # Используем фикстуру медиа
):
    """Тест успешного создания твита с медиа."""
    tweet_data = {
        "tweet_data": "Tweet with media!",
        "tweet_media_ids": [test_media.id]  # Используем ID из фикстуры
    }
    response = await async_client.post("/api/tweets", json=tweet_data, headers=nick_headers)

    assert response.status_code == status.HTTP_201_CREATED
    result = TweetCreateResult(**response.json())
    assert result.result is True
    assert isinstance(result.tweet_id, int)


async def test_create_tweet_with_invalid_media_id(
        async_client: AsyncClient,
        nick_headers: dict,
):
    """Тест создания твита с несуществующим media_id."""
    tweet_data = {
        "tweet_data": "Tweet with bad media!",
        "tweet_media_ids": [9999]  # Несуществующий ID
    }
    response = await async_client.post("/api/tweets", json=tweet_data, headers=nick_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"
    assert "9999" in data["error_message"]


async def test_create_tweet_unauthorized(async_client: AsyncClient):
    """Тест создания твита без api-key."""
    tweet_data = {"tweet_data": "Unauthorized tweet"}
    response = await async_client.post("/api/tweets", json=tweet_data)  # Без заголовка

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "unauthorized"


async def test_create_tweet_invalid_data(async_client: AsyncClient, nick_headers: dict):
    """Тест создания твита с невалидными данными (пустой текст)."""
    tweet_data = {"tweet_data": ""}  # Пустой текст не пройдет валидацию схемы
    response = await async_client.post("/api/tweets", json=tweet_data, headers=nick_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "Validation Error"  # Ошибка валидации Pydantic


# --- Тесты удаления твитов ---

async def test_delete_tweet_success(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,
        db_session: AsyncSession  # Нужна сессия для создания твита
):
    """Тест успешного удаления своего твита."""
    # Создаем твит напрямую в БД для теста
    tweet = Tweet(content="Tweet to be deleted", author_id=test_user_nick.id)
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    tweet_id_to_delete = tweet.id

    response = await async_client.delete(f"/api/tweets/{tweet_id_to_delete}", headers=nick_headers)

    assert response.status_code == status.HTTP_200_OK
    result = TweetActionResult(**response.json())
    assert result.result is True

    # Проверяем, что твит действительно удален
    deleted_tweet = await db_session.get(Tweet, tweet_id_to_delete)
    assert deleted_tweet is None


async def test_delete_tweet_not_found(async_client: AsyncClient, nick_headers: dict):
    """Тест удаления несуществующего твита."""
    response = await async_client.delete("/api/tweets/99999", headers=nick_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


async def test_delete_tweet_forbidden(
        async_client: AsyncClient,
        bob_headers: dict,  # Используем заголовки Боба
        tweet_from_alice: Tweet  # Используем твит от Алисы
):
    """Тест попытки удаления чужого твита."""
    response = await async_client.delete(f"/api/tweets/{tweet_from_alice.id}", headers=bob_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "permission_denied"


# --- Тесты лайков --- (Аналогично созданию/удалению)

async def test_like_tweet_success(
        async_client: AsyncClient,
        nick_headers: dict,
        tweet_from_alice: Tweet,
        test_user_nick: User,
        db_session: AsyncSession,
):
    """Тест успешного лайка твита."""
    tweet_id_to_like = tweet_from_alice.id
    response = await async_client.post(f"/api/tweets/{tweet_id_to_like}/likes", headers=nick_headers)

    assert response.status_code == status.HTTP_201_CREATED
    result = TweetActionResult(**response.json())
    assert result.result is True

    # Проверка лайка в БД
    like = await db_session.get(Like, (test_user_nick.id, tweet_id_to_like))
    assert like is not None


async def test_like_tweet_twice_conflict(
        async_client: AsyncClient,
        nick_headers: dict,
        tweet_from_alice: Tweet,
):
    """Тест повторного лайка (конфликт)."""
    tweet_id_to_like = tweet_from_alice.id
    # Первый лайк
    await async_client.post(f"/api/tweets/{tweet_id_to_like}/likes", headers=nick_headers)
    # Второй лайк
    response = await async_client.post(f"/api/tweets/{tweet_id_to_like}/likes", headers=nick_headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "conflict_error"


async def test_unlike_tweet_success(
        async_client: AsyncClient,
        nick_headers: dict,
        tweet_from_alice: Tweet,
        test_user_nick: User,
        db_session: AsyncSession,
):
    """Тест успешного снятия лайка."""
    tweet_id_to_unlike = tweet_from_alice.id
    # Сначала ставим лайк
    like = Like(user_id=test_user_nick.id, tweet_id=tweet_id_to_unlike)
    db_session.add(like)
    await db_session.commit()

    # Затем снимаем лайк через API
    response = await async_client.delete(f"/api/tweets/{tweet_id_to_unlike}/likes", headers=nick_headers)

    assert response.status_code == status.HTTP_200_OK
    result = TweetActionResult(**response.json())
    assert result.result is True

    # Проверяем, что лайк удален
    deleted_like = await db_session.get(Like, (test_user_nick.id, tweet_id_to_unlike))
    assert deleted_like is None


async def test_unlike_tweet_not_found(
        async_client: AsyncClient,
        nick_headers: dict,
        tweet_from_alice: Tweet,
):
    """Тест снятия несуществующего лайка."""
    response = await async_client.delete(f"/api/tweets/{tweet_from_alice.id}/likes", headers=nick_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "not_found"


# --- Тест ленты твитов ---

async def test_get_feed(
        async_client: AsyncClient,
        nick_headers: dict,
        test_user_nick: User,
        test_user_alice: User,
        tweet_from_alice: Tweet,  # Используем твит от Alice
        db_session: AsyncSession
):
    """Тест получения ленты твитов."""
    # Создаем подписку Nick -> Alice
    follow = Follow(follower_id=test_user_nick.id, following_id=test_user_alice.id)
    db_session.add(follow)
    # Создаем собственный твит Nick'а
    nick_tweet = Tweet(content="Nick's own tweet", author_id=test_user_nick.id)
    db_session.add(nick_tweet)
    await db_session.commit()

    response = await async_client.get("/api/tweets", headers=nick_headers)

    assert response.status_code == status.HTTP_200_OK
    data = TweetFeedResult(**response.json())
    assert data.result is True
    assert len(data.tweets) == 2  # Должен быть твит Alice и твит Nick

    # Проверяем, что твиты пришли в правильном формате
    tweet_ids_in_feed = {t.id for t in data.tweets}
    assert tweet_from_alice.id in tweet_ids_in_feed
    assert nick_tweet.id in tweet_ids_in_feed

    # Проверяем содержимое одного твита (например, от Alice)
    alice_tweet_in_feed = next(t for t in data.tweets if t.id == tweet_from_alice.id)
    assert alice_tweet_in_feed.content == tweet_from_alice.content
    assert alice_tweet_in_feed.author.id == test_user_alice.id
    assert alice_tweet_in_feed.author.name == test_user_alice.name
    assert isinstance(alice_tweet_in_feed.likes, list)
    assert isinstance(alice_tweet_in_feed.attachments, list)
