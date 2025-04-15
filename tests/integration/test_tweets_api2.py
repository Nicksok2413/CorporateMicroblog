import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models import Like, Media, Tweet, User

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тесты на создание твита ---

async def test_create_tweet_success_no_media(
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession  # Добавляем сессию для проверки БД
):
    """Тест успешного создания твита без медиа."""
    tweet_data = {"tweet_data": "My first test tweet!"}
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    assert "tweet_id" in json_response
    new_tweet_id = json_response["tweet_id"]
    assert new_tweet_id > 0

    # Проверяем, что твит реально создался в БД
    tweet_in_db = await db_session.get(Tweet, new_tweet_id)
    assert tweet_in_db is not None
    assert tweet_in_db.content == tweet_data["tweet_data"]
    assert tweet_in_db.author_id == test_user.id
    # Проверяем, что медиа не привязаны
    assert not tweet_in_db.attachments


async def test_create_tweet_too_long(authenticated_client: AsyncClient):
    """Тест создания твита со слишком длинным текстом."""
    long_text = "a" * 281  # 281 символ
    tweet_data = {"tweet_data": long_text}
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    # Ожидаем ошибку валидации 422
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "Validation Error"
    assert "tweet_data" in json_response["error_message"]
    assert "280" in json_response["error_message"]  # Проверяем упоминание лимита


async def test_create_tweet_empty(authenticated_client: AsyncClient):
    """Тест создания твита с пустым текстом."""
    tweet_data = {"tweet_data": ""}
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    # Ожидаем ошибку валидации 422
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "Validation Error"
    assert "tweet_data" in json_response["error_message"]


async def test_create_tweet_unauthorized(client: AsyncClient):
    """Тест создания твита без аутентификации."""
    tweet_data = {"tweet_data": "Should not work"}
    response = await client.post("/api/tweets", json=tweet_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты на создание твита с медиа ---

async def test_create_tweet_with_media_success(
        authenticated_client: AsyncClient,
        test_user: User,
        uploaded_media: Media,  # Используем фикстуру для загруженного медиа
        db_session: AsyncSession
):
    """Тест успешного создания твита с одним медиа."""
    tweet_data = {
        "tweet_data": "Tweet with media!",
        "tweet_media_ids": [uploaded_media.id]  # Передаем ID загруженного медиа
    }
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    new_tweet_id = json_response["tweet_id"]

    # Проверяем твит в БД
    tweet_in_db = await db_session.get(Tweet, new_tweet_id)
    assert tweet_in_db is not None
    assert tweet_in_db.content == tweet_data["tweet_data"]
    assert tweet_in_db.author_id == test_user.id

    # Проверяем медиа в БД
    await db_session.refresh(uploaded_media)  # Обновляем объект media
    assert uploaded_media is not None
    assert uploaded_media.tweet_id == new_tweet_id  # Проверяем, что tweet_id установился

    # Проверяем связь через твит
    await db_session.refresh(tweet_in_db, attribute_names=['attachments'])  # Обновляем твит со связью
    assert len(tweet_in_db.attachments) == 1
    assert tweet_in_db.attachments[0].id == uploaded_media.id


async def test_create_tweet_with_nonexistent_media(authenticated_client: AsyncClient):
    """Тест создания твита с несуществующим media_id."""
    tweet_data = {
        "tweet_data": "Tweet with bad media!",
        "tweet_media_ids": [99999]  # Несуществующий ID
    }
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
    assert "Медиафайл с ID 99999 не найден" in json_response["error_message"]


async def test_create_tweet_with_multiple_media(
        authenticated_client: AsyncClient,
        test_user: User,
        uploaded_media_list: list[Media],
        db_session: AsyncSession
):
    """Тест успешного создания твита с несколькими медиа."""
    media_ids = [m.id for m in uploaded_media_list]
    assert len(media_ids) == 2  # Убедимся, что фикстура вернула 2 медиа

    tweet_data = {
        "tweet_data": "Tweet with multiple media!",
        "tweet_media_ids": media_ids
    }
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    new_tweet_id = json_response["tweet_id"]

    tweet_in_db = await db_session.get(Tweet, new_tweet_id)
    assert tweet_in_db is not None
    assert tweet_in_db.author_id == test_user.id

    # Проверяем, что оба медиа привязались
    for media in uploaded_media_list:
        await db_session.refresh(media)
        assert media.tweet_id == new_tweet_id

    await db_session.refresh(tweet_in_db, attribute_names=['attachments'])
    assert len(tweet_in_db.attachments) == 2
    # Проверяем ID привязанных медиа (сортируем для стабильности теста)
    attached_ids = sorted([a.id for a in tweet_in_db.attachments])
    expected_ids = sorted(media_ids)
    assert attached_ids == expected_ids


# --- Тесты на получение ленты твитов ---

async def test_get_tweet_feed_success(
        authenticated_client: AsyncClient,
        feed_setup: dict
):
    """Тест успешного получения ленты твитов."""
    response = await authenticated_client.get("/api/tweets")

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    tweets_in_feed = json_response["tweets"]

    # Ожидаем 3 твита: свой и два от alice
    assert len(tweets_in_feed) == 3

    # Проверяем ID твитов (порядок может зависеть от сортировки по лайкам)
    feed_tweet_ids = {t["id"] for t in tweets_in_feed}
    expected_ids = {
        feed_setup["tweet_user_id"],
        feed_setup["tweet_alice_1_id"],
        feed_setup["tweet_alice_2_id"]
    }
    assert feed_tweet_ids == expected_ids

    # Проверяем структуру одного из твитов (например, tweet_alice_2 с медиа и 2 лайками)
    tweet_alice_2_data = next((t for t in tweets_in_feed if t["id"] == feed_setup["tweet_alice_2_id"]), None)
    assert tweet_alice_2_data is not None
    assert tweet_alice_2_data["content"] == "Alice's tweet 2 with media"
    assert tweet_alice_2_data["author"]["id"] == feed_setup["alice"].id
    assert tweet_alice_2_data["author"]["name"] == feed_setup["alice"].name

    # Проверяем лайки
    assert len(tweet_alice_2_data["likes"]) == 2
    liker_ids = {like["user_id"] for like in tweet_alice_2_data["likes"]}
    assert liker_ids == {feed_setup["user"].id, feed_setup["bob"].id}
    # Проверяем, что имена лайкнувших тоже есть
    assert all("name" in like for like in tweet_alice_2_data["likes"])

    # Проверяем медиа
    assert len(tweet_alice_2_data["attachments"]) == 1
    # Проверяем, что это URL, сформированный правильно
    media_url = tweet_alice_2_data["attachments"][0]
    expected_media_path = feed_setup["media"].file_path
    expected_url_part = f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/{expected_media_path.lstrip('/')}"
    assert media_url == expected_url_part

    # Проверим сортировку (tweet_alice_2 с 2 лайками должен быть выше, чем tweet_alice_1 с 1 лайком)
    # Если сортировка по ID вторична, то tweet_user (1 лайк) может быть между ними или последним
    ids_ordered = [t["id"] for t in tweets_in_feed]
    assert ids_ordered[0] == feed_setup["tweet_alice_2_id"]  # 2 лайка - первый


async def test_get_tweet_feed_empty(authenticated_client: AsyncClient):
    """Тест получения пустой ленты (пользователь ни на кого не подписан и не имеет твитов)."""
    response = await authenticated_client.get("/api/tweets")

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    assert json_response["tweets"] == []


async def test_get_tweet_feed_unauthorized(client: AsyncClient):
    """Тест получения ленты без аутентификации."""
    response = await client.get("/api/tweets")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты на удаление твитов ---

async def test_delete_tweet_success_no_media(
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession
):
    """Тест успешного удаления своего твита без медиа."""
    # Создаем твит
    tweet = Tweet(author_id=test_user.id, content="Tweet to delete")
    db_session.add(tweet)
    await db_session.commit()
    tweet_id = tweet.id

    # Удаляем через API
    response = await authenticated_client.delete(f"/api/tweets/{tweet_id}")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем, что твит удален из БД
    tweet_in_db = await db_session.get(Tweet, tweet_id)
    assert tweet_in_db is None


async def test_delete_tweet_success_with_media(
        authenticated_client: AsyncClient,
        test_user: User,
        uploaded_media: Media,  # Используем фикстуру для медиа
        db_session: AsyncSession
):
    """Тест успешного удаления своего твита с медиа."""
    # Создаем твит и привязываем медиа
    tweet = Tweet(author_id=test_user.id, content="Tweet with media to delete")
    db_session.add(tweet)
    await db_session.flush()  # Получаем ID твита
    tweet_id = tweet.id
    media_id = uploaded_media.id
    media_path = settings.MEDIA_ROOT_PATH / uploaded_media.file_path  # Запоминаем путь к файлу
    uploaded_media.tweet_id = tweet_id
    await db_session.commit()

    # Проверяем, что файл существует ДО удаления
    assert media_path.exists()

    # Удаляем твит через API
    response = await authenticated_client.delete(f"/api/tweets/{tweet_id}")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем, что твит удален из БД
    tweet_in_db = await db_session.get(Tweet, tweet_id)
    assert tweet_in_db is None

    # Проверяем, что медиа запись удалена из БД (из-за CASCADE)
    media_in_db = await db_session.get(Media, media_id)
    assert media_in_db is None

    # Проверяем, что физический файл удален
    # Используем синхронную проверку, т.к. удаление могло быть в другом потоке
    assert not media_path.exists()


async def test_delete_tweet_forbidden(
        authenticated_client: AsyncClient,  # Клиент test_user
        test_user_alice: User,
        db_session: AsyncSession
):
    """Тест попытки удалить чужой твит."""
    # Создаем твит от alice
    tweet = Tweet(author_id=test_user_alice.id, content="Alice's tweet")
    db_session.add(tweet)
    await db_session.commit()
    tweet_id = tweet.id

    # Пытаемся удалить от test_user
    response = await authenticated_client.delete(f"/api/tweets/{tweet_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "permission_denied"

    # Проверяем, что твит остался в БД
    tweet_in_db = await db_session.get(Tweet, tweet_id)
    assert tweet_in_db is not None


async def test_delete_tweet_not_found(authenticated_client: AsyncClient):
    """Тест попытки удалить несуществующий твит."""
    response = await authenticated_client.delete("/api/tweets/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


async def test_delete_tweet_unauthorized(client: AsyncClient):
    """Тест удаления твита без аутентификации."""
    # Нужен ID существующего твита, но т.к. БД чистая, просто используем любой ID
    response = await client.delete("/api/tweets/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты для лайков ---

async def test_like_tweet_success(
        authenticated_client: AsyncClient,  # Клиент test_user
        tweet_for_likes: Tweet,
        test_user: User,
        db_session: AsyncSession
):
    """Тест успешного лайка твита."""
    tweet_id = tweet_for_likes.id
    response = await authenticated_client.post(f"/api/tweets/{tweet_id}/likes")

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем наличие лайка в БД
    like_in_db = await db_session.execute(
        select(Like).where(Like.user_id == test_user.id, Like.tweet_id == tweet_id)
    )
    assert like_in_db.scalar_one_or_none() is not None


async def test_like_tweet_not_found(authenticated_client: AsyncClient):
    """Тест лайка несуществующего твита."""
    response = await authenticated_client.post("/api/tweets/99999/likes")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
    assert f"Твит с ID 99999 не найден" in json_response["error_message"]


async def test_like_tweet_unauthorized(client: AsyncClient, tweet_for_likes: Tweet):
    """Тест лайка без аутентификации."""
    response = await client.post(f"/api/tweets/{tweet_for_likes.id}/likes")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты для удаления лайков ---

async def test_unlike_tweet_success(
        authenticated_client: AsyncClient,
        tweet_for_likes: Tweet,
        test_user: User,
        db_session: AsyncSession
):
    """Тест успешного удаления лайка."""
    tweet_id = tweet_for_likes.id
    # Сначала ставим лайк
    like = Like(user_id=test_user.id, tweet_id=tweet_id)
    db_session.add(like)
    await db_session.commit()

    # Удаляем лайк через API
    response = await authenticated_client.delete(f"/api/tweets/{tweet_id}/likes")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True

    # Проверяем, что лайк удален из БД
    like_in_db = await db_session.execute(
        select(Like).where(Like.user_id == test_user.id, Like.tweet_id == tweet_id)
    )
    assert like_in_db.scalar_one_or_none() is None


async def test_unlike_tweet_not_found_like(
        authenticated_client: AsyncClient,
        tweet_for_likes: Tweet
):
    """Тест удаления несуществующего лайка (твит не был лайкнут)."""
    response = await authenticated_client.delete(f"/api/tweets/{tweet_for_likes.id}/likes")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
    assert "Лайк не найден" in json_response["error_message"]


async def test_unlike_tweet_not_found_tweet(authenticated_client: AsyncClient):
    """Тест удаления лайка с несуществующего твита."""
    response = await authenticated_client.delete("/api/tweets/99999/likes")
    # Ожидаем 404, т.к. сервис сначала проверяет наличие лайка, которого не будет
    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"


async def test_unlike_tweet_unauthorized(client: AsyncClient, tweet_for_likes: Tweet):
    """Тест удаления лайка без аутентификации."""
    response = await client.delete(f"/api/tweets/{tweet_for_likes.id}/likes")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
