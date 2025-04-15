import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import User, Tweet, Media, Like  # Нужны для проверок и типизации
from src.core.config import settings  # Нужен API_KEY_HEADER

pytestmark = pytest.mark.asyncio


# Вспомогательная функция для загрузки медиа
async def upload_test_media(client: AsyncClient) -> int:
    files = {'file': ('test_image.png', b'fake png data', 'image/png')}
    response = await client.post("/api/media", files=files)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["media_id"]


# === POST /api/tweets ===

async def test_create_tweet_unauthorized(client: AsyncClient):
    payload = {"tweet_data": "My first tweet"}
    response = await client.post("/api/tweets", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_create_tweet_simple_success(authenticated_client: AsyncClient, test_user_nick: User,
                                           db_session: AsyncSession):
    tweet_text = "A simple tweet without media."
    payload = {"tweet_data": tweet_text}
    response = await authenticated_client.post("/api/tweets", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    assert "tweet_id" in json_response
    tweet_id = json_response["tweet_id"]
    assert tweet_id > 0

    # Проверяем в БД
    tweet = await db_session.get(Tweet, tweet_id)
    assert tweet is not None
    assert tweet.id == tweet_id
    assert tweet.content == tweet_text
    assert tweet.author_id == test_user.id
    assert tweet.attachments == []  # В SQLAlchemy 2.0 пустая коллекция


async def test_create_tweet_with_media_success(authenticated_client: AsyncClient, test_user_nick: User,
                                               db_session: AsyncSession):
    # Сначала загружаем медиа
    media_id = await upload_test_media(authenticated_client)

    tweet_text = "Tweet with media!"
    payload = {"tweet_data": tweet_text, "tweet_media_ids": [media_id]}
    response = await authenticated_client.post("/api/tweets", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    tweet_id = json_response["tweet_id"]

    # Проверяем твит в БД
    tweet = await db_session.get(Tweet, tweet_id)
    assert tweet is not None
    assert tweet.content == tweet_text
    assert tweet.author_id == test_user.id

    # Проверяем медиа в БД
    media = await db_session.get(Media, media_id)
    assert media is not None
    assert media.tweet_id == tweet_id  # Проверяем связь

    # Проверяем связь через ORM (если нужно)
    await db_session.refresh(tweet, attribute_names=['attachments'])
    assert len(tweet.attachments) == 1
    assert tweet.attachments[0].id == media_id


async def test_create_tweet_with_nonexistent_media(authenticated_client: AsyncClient):
    payload = {"tweet_data": "Bad media", "tweet_media_ids": [9999]}
    response = await authenticated_client.post("/api/tweets", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_create_tweet_with_used_media(authenticated_client: AsyncClient, test_user_nick: User):
    # Загружаем медиа
    media_id = await upload_test_media(authenticated_client)
    # Создаем первый твит с этим медиа
    await authenticated_client.post("/api/tweets", json={"tweet_data": "First tweet", "tweet_media_ids": [media_id]})
    # Пытаемся создать второй твит с тем же медиа ID
    payload = {"tweet_data": "Second tweet", "tweet_media_ids": [media_id]}
    response = await authenticated_client.post("/api/tweets", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT  # Ошибка, что медиа уже использовано


async def test_create_tweet_invalid_data(authenticated_client: AsyncClient):
    # Слишком длинный твит
    long_text = "a" * 281
    payload = {"tweet_data": long_text}
    response = await authenticated_client.post("/api/tweets", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Пустой твит
    payload = {"tweet_data": ""}
    response = await authenticated_client.post("/api/tweets", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# === GET /api/tweets (Feed) ===

async def test_get_feed_unauthorized(client: AsyncClient):
    response = await client.get("/api/tweets")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_feed_empty(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/tweets")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["result"] is True
    assert json_response["tweets"] == []


async def test_get_feed_with_own_tweets(authenticated_client: AsyncClient, test_user_nick: User):
    # Создаем твит
    payload = {"tweet_data": "My own tweet"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]

    # Получаем ленту
    response_get = await authenticated_client.get("/api/tweets")
    assert response_get.status_code == status.HTTP_200_OK
    tweets = response_get.json()["tweets"]
    assert len(tweets) == 1
    assert tweets[0]["id"] == tweet_id
    assert tweets[0]["content"] == "My own tweet"
    assert tweets[0]["author"]["id"] == test_user.id
    assert tweets[0]["author"]["name"] == test_user.name
    assert tweets[0]["likes"] == []
    assert tweets[0]["attachments"] == []


async def test_get_feed_with_followed_tweets(
        authenticated_client: AsyncClient,  # Nick
        client: AsyncClient,  # Для Alice
        test_user_nick: User,
        test_user_alice: User,
        db_session: AsyncSession  # Нужен для лайков и проверки
):
    # Alice создает твит
    client.headers[settings.API_KEY_HEADER] = test_user_alice.api_key  # Клиент Alice
    payload_alice = {"tweet_data": "Alice's tweet"}
    response_post_alice = await client.post("/api/tweets", json=payload_alice)
    alice_tweet_id = response_post_alice.json()["tweet_id"]

    # Nick подписывается на Alice
    await authenticated_client.post(f"/api/users/{test_user_alice.id}/follow")

    # Nick создает свой твит
    payload_nick = {"tweet_data": "Nick's tweet"}
    response_post_nick = await authenticated_client.post("/api/tweets", json=payload_nick)
    nick_tweet_id = response_post_nick.json()["tweet_id"]

    # Nick лайкает твит Alice
    await authenticated_client.post(f"/api/tweets/{alice_tweet_id}/likes")

    # Получаем ленту Nick'а
    response_feed = await authenticated_client.get("/api/tweets")
    assert response_feed.status_code == status.HTTP_200_OK
    feed_data = response_feed.json()
    assert feed_data["result"] is True
    tweets_in_feed = feed_data["tweets"]
    assert len(tweets_in_feed) == 2

    # Проверяем содержимое (сортировка по лайкам -> дате не гарантирована жестко)
    tweet_ids_in_feed = {t["id"] for t in tweets_in_feed}
    assert tweet_ids_in_feed == {nick_tweet_id, alice_tweet_id}

    # Проверяем твит Alice в ленте Nick'а
    alice_tweet_in_feed = next(t for t in tweets_in_feed if t["id"] == alice_tweet_id)
    assert alice_tweet_in_feed["content"] == "Alice's tweet"
    assert alice_tweet_in_feed["author"]["id"] == test_user_alice.id
    assert len(alice_tweet_in_feed["likes"]) == 1
    assert alice_tweet_in_feed["likes"][0]["user_id"] == test_user.id  # Проверяем алиас user_id
    assert alice_tweet_in_feed["likes"][0]["name"] == test_user.name

    # Проверяем твит Nick'а в ленте Nick'а
    nick_tweet_in_feed = next(t for t in tweets_in_feed if t["id"] == nick_tweet_id)
    assert nick_tweet_in_feed["content"] == "Nick's tweet"
    assert nick_tweet_in_feed["author"]["id"] == test_user.id
    assert len(nick_tweet_in_feed["likes"]) == 0


# === DELETE /api/tweets/{tweet_id} ===

async def test_delete_tweet_unauthorized(client: AsyncClient):
    # Нужен ID твита, но без авторизации он не важен
    response = await client.delete("/api/tweets/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_delete_non_existent_tweet(authenticated_client: AsyncClient):
    response = await authenticated_client.delete("/api/tweets/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_other_user_tweet(
        authenticated_client: AsyncClient,  # Nick
        client: AsyncClient,  # Alice
        test_user_alice: User
):
    # Alice создает твит
    client.headers[settings.API_KEY_HEADER] = test_user_alice.api_key
    payload_alice = {"tweet_data": "Alice's deletable tweet"}
    response_post_alice = await client.post("/api/tweets", json=payload_alice)
    alice_tweet_id = response_post_alice.json()["tweet_id"]

    # Nick пытается удалить твит Alice
    response = await authenticated_client.delete(f"/api/tweets/{alice_tweet_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_delete_own_tweet_success(authenticated_client: AsyncClient, db_session: AsyncSession):
    # Создаем твит
    payload = {"tweet_data": "Tweet to be deleted"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]

    # Проверяем, что он есть
    tweet_before = await db_session.get(Tweet, tweet_id)
    assert tweet_before is not None

    # Удаляем
    response_delete = await authenticated_client.delete(f"/api/tweets/{tweet_id}")
    assert response_delete.status_code == status.HTTP_200_OK
    assert response_delete.json()["result"] is True

    # Проверяем, что его нет
    await db_session.flush()  # Обновляем состояние сессии
    tweet_after = await db_session.get(Tweet, tweet_id)
    assert tweet_after is None


async def test_delete_own_tweet_with_media_success(authenticated_client: AsyncClient, db_session: AsyncSession):
    # Загружаем медиа
    media_id = await upload_test_media(authenticated_client)
    # Создаем твит
    payload = {"tweet_data": "Tweet with media to delete", "tweet_media_ids": [media_id]}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]

    # Проверяем наличие твита и медиа
    tweet_before = await db_session.get(Tweet, tweet_id)
    media_before = await db_session.get(Media, media_id)
    assert tweet_before is not None
    assert media_before is not None
    assert media_before.tweet_id == tweet_id

    # Удаляем твит
    response_delete = await authenticated_client.delete(f"/api/tweets/{tweet_id}")
    assert response_delete.status_code == status.HTTP_200_OK

    # Проверяем удаление из БД
    await db_session.flush()
    tweet_after = await db_session.get(Tweet, tweet_id)
    media_after = await db_session.get(Media, media_id)
    assert tweet_after is None
    assert media_after is None  # Должно удалиться каскадно!

    # TODO: Проверить физическое удаление файла (сложно автоматизировать)


# === POST /api/tweets/{tweet_id}/likes ===

async def test_like_tweet_unauthorized(client: AsyncClient):
    response = await client.post("/api/tweets/1/likes")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_like_non_existent_tweet(authenticated_client: AsyncClient):
    response = await authenticated_client.post("/api/tweets/9999/likes")
    assert response.status_code == status.HTTP_404_NOT_FOUND  # Ошибка от TweetService (проверка твита)


async def test_like_tweet_success(authenticated_client: AsyncClient, test_user_nick: User, db_session: AsyncSession):
    # Создаем твит
    payload = {"tweet_data": "Tweet to be liked"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]

    # Лайкаем
    response_like = await authenticated_client.post(f"/api/tweets/{tweet_id}/likes")
    assert response_like.status_code == status.HTTP_201_CREATED
    assert response_like.json()["result"] is True

    # Проверяем лайк в БД
    like = await db_session.get(Like, (test_user.id, tweet_id))
    assert like is not None
    assert like.user_id == test_user.id
    assert like.tweet_id == tweet_id


async def test_like_already_liked_tweet(authenticated_client: AsyncClient):
    # Создаем твит
    payload = {"tweet_data": "Tweet to be liked twice"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]
    # Лайкаем первый раз
    await authenticated_client.post(f"/api/tweets/{tweet_id}/likes")
    # Лайкаем второй раз
    response_like = await authenticated_client.post(f"/api/tweets/{tweet_id}/likes")
    assert response_like.status_code == status.HTTP_409_CONFLICT


# === DELETE /api/tweets/{tweet_id}/likes ===

async def test_unlike_tweet_unauthorized(client: AsyncClient):
    response = await client.delete("/api/tweets/1/likes")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_unlike_non_existent_tweet(authenticated_client: AsyncClient):
    # Твит может существовать, но лайка на нем нет
    payload = {"tweet_data": "Tweet exists but no like"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]

    response = await authenticated_client.delete(f"/api/tweets/{tweet_id}/likes")
    assert response.status_code == status.HTTP_404_NOT_FOUND  # Лайк не найден


async def test_unlike_tweet_not_liked(authenticated_client: AsyncClient):
    # Создаем твит, но не лайкаем его
    payload = {"tweet_data": "Tweet never liked"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]

    # Пытаемся убрать лайк
    response = await authenticated_client.delete(f"/api/tweets/{tweet_id}/likes")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_unlike_tweet_success(authenticated_client: AsyncClient, test_user_nick: User, db_session: AsyncSession):
    # Создаем твит
    payload = {"tweet_data": "Tweet to unlike"}
    response_post = await authenticated_client.post("/api/tweets", json=payload)
    tweet_id = response_post.json()["tweet_id"]
    # Лайкаем
    await authenticated_client.post(f"/api/tweets/{tweet_id}/likes")
    # Проверяем, что лайк есть
    like_before = await db_session.get(Like, (test_user.id, tweet_id))
    assert like_before is not None

    # Убираем лайк
    response_unlike = await authenticated_client.delete(f"/api/tweets/{tweet_id}/likes")
    assert response_unlike.status_code == status.HTTP_200_OK
    assert response_unlike.json()["result"] is True

    # Проверяем, что лайка нет
    await db_session.flush()
    like_after = await db_session.get(Like, (test_user.id, tweet_id))
    assert like_after is None
