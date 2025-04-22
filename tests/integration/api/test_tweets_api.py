import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Awaitable, Callable, List

from src.core.config import settings
from src.models import Follow, Like, Media, Tweet, User

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тесты на создание твита ---


async def test_create_tweet_success_no_media(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,  # Добавляем сессию для проверки БД
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


async def test_create_tweet_with_one_media(
    authenticated_client: AsyncClient,
    test_user: User,
    create_uploaded_media_list: Callable[[int], Awaitable[List[Media]]],
    db_session: AsyncSession,
):
    """Тест успешного создания твита с одним медиа ."""
    # Вызываем фабрику для создания 1 медиа
    uploaded_media_list = await create_uploaded_media_list(count=1)
    assert len(uploaded_media_list) == 1
    uploaded_media = uploaded_media_list[0]  # Берем первый (и единственный) элемент

    tweet_data = {
        "tweet_data": "Tweet with one media from factory!",
        "tweet_media_ids": [uploaded_media.id],
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
    assert (
        uploaded_media.tweet_id == new_tweet_id
    )  # Проверяем, что tweet_id установился

    # Проверяем связь через твит
    await db_session.refresh(
        tweet_in_db, attribute_names=["attachments"]
    )  # Обновляем твит со связью
    assert len(tweet_in_db.attachments) == 1
    assert tweet_in_db.attachments[0].id == uploaded_media.id


async def test_create_tweet_with_multiple_media(
    authenticated_client: AsyncClient,
    test_user: User,
    create_uploaded_media_list: Callable[[int], Awaitable[List[Media]]],
    db_session: AsyncSession,
):
    """Тест успешного создания твита с тремя медиа."""
    # Вызываем фабрику, чтобы создать 3 медиафайла
    uploaded_media_list = await create_uploaded_media_list(count=3)
    assert len(uploaded_media_list) == 3  # Убедимся, что фабрика сработала

    media_ids = [media.id for media in uploaded_media_list]

    tweet_data = {
        "tweet_data": "Tweet with 3 media items!",
        "tweet_media_ids": media_ids,
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

    # Проверяем, что все медиа привязались
    for media in uploaded_media_list:
        await db_session.refresh(media)
        assert media.tweet_id == new_tweet_id

    await db_session.refresh(
        tweet_in_db, attribute_names=["attachments"]
    )  # Обновляем объекты media
    assert len(tweet_in_db.attachments) == 3

    # Проверяем ID привязанных медиа (сортируем для стабильности теста)
    attached_ids = sorted([attachment.id for attachment in tweet_in_db.attachments])
    expected_ids = sorted(media_ids)
    assert attached_ids == expected_ids


async def test_create_tweet_with_nonexistent_media(authenticated_client: AsyncClient):
    """Тест создания твита с несуществующим media_id."""
    tweet_data = {
        "tweet_data": "Tweet with bad media!",
        "tweet_media_ids": [99999],  # Несуществующий ID
    }
    response = await authenticated_client.post("/api/tweets", json=tweet_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "not_found"
    assert "Медиафайл с ID 99999 не найден" in json_response["error_message"]


# --- Тесты на удаление твитов ---


async def test_delete_tweet_success_no_media(
    authenticated_client: AsyncClient, test_user: User, db_session: AsyncSession
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
    create_uploaded_media_list: Callable[[int], Awaitable[List[Media]]],
    db_session: AsyncSession,
):
    """Тест успешного удаления своего твита с медиа."""
    # Создаем медиа
    uploaded_media_list = await create_uploaded_media_list(count=1)
    assert len(uploaded_media_list) == 1

    # Создаем твит и привязываем медиа
    tweet = Tweet(author_id=test_user.id, content="Tweet with media to delete")
    db_session.add(tweet)
    await db_session.flush()  # Получаем ID твита

    tweet_id = tweet.id
    media_id = uploaded_media_list[0].id
    media_path = (
        settings.MEDIA_ROOT_PATH / uploaded_media_list[0].file_path
    )  # Запоминаем путь к файлу
    uploaded_media_list[0].tweet_id = tweet_id
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
    db_session: AsyncSession,
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


# --- Тесты на получение ленты твитов ---


# # Фикстура создания состояния системы
@pytest_asyncio.fixture(scope="function")
async def feed_setup(
    db_session: AsyncSession,
    test_user: User,
    test_user_alice: User,
    test_user_bob: User,
    create_uploaded_media_list: Callable[[int], Awaitable[List[Media]]],
):
    """Настраивает данные для тестов ленты: пользователи, подписки, твиты, лайки."""
    # 1. Подписки: test_user -> alice
    follow = Follow(follower_id=test_user.id, following_id=test_user_alice.id)
    db_session.add(follow)

    # 2. Твиты
    tweet_user = Tweet(author_id=test_user.id, content="My own tweet")
    tweet_alice_1 = Tweet(author_id=test_user_alice.id, content="Alice's tweet 1")
    tweet_alice_2 = Tweet(
        author_id=test_user_alice.id, content="Alice's tweet 2 with media"
    )
    tweet_bob = Tweet(
        author_id=test_user_bob.id, content="Bob's tweet (should not be in feed)"
    )
    db_session.add_all([tweet_user, tweet_alice_1, tweet_alice_2, tweet_bob])
    await db_session.flush()  # Получаем ID твитов

    # Создаем медиа
    uploaded_media_list = await create_uploaded_media_list(count=1)
    uploaded_media = uploaded_media_list[0]

    # Привязываем медиа к tweet_alice_2
    uploaded_media.tweet_id = tweet_alice_2.id
    # db_session.add(uploaded_media) # Не нужно, уже отслеживается

    # 3. Лайки (для проверки структуры и сортировки)
    # bob лайкает tweet_alice_1
    like1 = Like(user_id=test_user_bob.id, tweet_id=tweet_alice_1.id)
    # bob и test_user лайкают tweet_alice_2
    like2 = Like(user_id=test_user_bob.id, tweet_id=tweet_alice_2.id)
    like3 = Like(user_id=test_user.id, tweet_id=tweet_alice_2.id)
    # alice лайкает tweet_user
    like4 = Like(user_id=test_user_alice.id, tweet_id=tweet_user.id)
    db_session.add_all([like1, like2, like3, like4])

    await db_session.commit()
    # Возвращаем ID для проверок
    return {
        "user": test_user,
        "alice": test_user_alice,
        "bob": test_user_bob,
        "tweet_user_id": tweet_user.id,
        "tweet_alice_1_id": tweet_alice_1.id,
        "tweet_alice_2_id": tweet_alice_2.id,
        "tweet_bob_id": tweet_bob.id,
        "media": uploaded_media,
    }


async def test_get_tweet_feed_success_with_own_tweet(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Тест успешного получения ленты твитов с одним своим твитом."""
    # Создаем твит
    tweet = Tweet(author_id=test_user.id, content="My own tweet")
    db_session.add(tweet)
    await db_session.commit()
    tweet_id = tweet.id

    # Получаем ленту
    response = await authenticated_client.get("/api/tweets")
    assert response.status_code == status.HTTP_200_OK
    tweets = response.json()["tweets"]
    assert len(tweets) == 1
    assert tweets[0]["id"] == tweet_id
    assert tweets[0]["content"] == "My own tweet"
    assert tweets[0]["author"]["id"] == test_user.id
    assert tweets[0]["author"]["name"] == test_user.name
    assert tweets[0]["likes"] == []
    assert tweets[0]["attachments"] == []


async def test_get_tweet_feed_success(
    authenticated_client: AsyncClient, feed_setup: dict
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
    feed_tweet_ids = {tweet["id"] for tweet in tweets_in_feed}
    expected_ids = {
        feed_setup["tweet_user_id"],
        feed_setup["tweet_alice_1_id"],
        feed_setup["tweet_alice_2_id"],
    }
    assert feed_tweet_ids == expected_ids

    # Проверяем структуру одного из твитов (например, tweet_alice_2 с медиа и 2 лайками)
    tweet_alice_2_data = next(
        (
            tweet
            for tweet in tweets_in_feed
            if tweet["id"] == feed_setup["tweet_alice_2_id"]
        ),
        None,
    )
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
    expected_url_part = (
        f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/{expected_media_path.lstrip('/')}"
    )
    assert media_url == expected_url_part

    # Проверим сортировку:
    # tweet_alice_2 (2 лайка)
    # tweet_alice_1 (1 лайк, ID новее)
    # tweet_user (1 лайк, ID старше)
    ids_ordered = [tweet["id"] for tweet in tweets_in_feed]
    assert ids_ordered[0] == feed_setup["tweet_alice_2_id"]  # 2 лайка - первый

    # Теперь проверяем порядок твитов с 1 лайком
    # Найдем их индексы
    try:
        index_alice_1 = ids_ordered.index(feed_setup["tweet_alice_1_id"])
        index_user = ids_ordered.index(feed_setup["tweet_user_id"])
        # Проверяем, что тот, у кого ID больше (новее), идет раньше
        if feed_setup["tweet_alice_1_id"] > feed_setup["tweet_user_id"]:
            assert index_alice_1 < index_user
        else:
            assert index_user < index_alice_1
    except ValueError:
        pytest.fail("Один из ожидаемых твитов с 1 лайком не найден в ленте")


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


# --- Тесты для лайков ---


# Фикстура твита для лайков
@pytest_asyncio.fixture(scope="function")
async def tweet_for_likes(db_session: AsyncSession, test_user_alice: User) -> Tweet:
    """Фикстура, создающая твит для лайков."""
    tweet = Tweet(author_id=test_user_alice.id, content="Tweet for likes")
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    return tweet


async def test_like_tweet_success(
    authenticated_client: AsyncClient,  # Клиент test_user
    tweet_for_likes: Tweet,
    test_user: User,
    db_session: AsyncSession,
):
    """Тест успешного лайка твита."""
    # Лайкаем
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
    assert "Твит с ID 99999 не найден" in json_response["error_message"]


async def test_like_tweet_unauthorized(client: AsyncClient, tweet_for_likes: Tweet):
    """Тест лайка без аутентификации."""
    response = await client.post(f"/api/tweets/{tweet_for_likes.id}/likes")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты для удаления лайков ---


async def test_unlike_tweet_success(
    authenticated_client: AsyncClient,
    tweet_for_likes: Tweet,
    test_user: User,
    db_session: AsyncSession,
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
    authenticated_client: AsyncClient, tweet_for_likes: Tweet
):
    """Тест удаления несуществующего лайка (твит не был лайкнут)."""
    response = await authenticated_client.delete(
        f"/api/tweets/{tweet_for_likes.id}/likes"
    )
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
