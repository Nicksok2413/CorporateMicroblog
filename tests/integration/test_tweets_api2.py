import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Tweet, Media

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

    # Проверяем, что твит реально создался в БД
    tweet_in_db = await db_session.get(Tweet, new_tweet_id)
    assert tweet_in_db is not None
    assert tweet_in_db.content == tweet_data["tweet_data"]
    assert tweet_in_db.author_id == test_user.id
    # Проверяем, что медиа не привязаны
    assert not tweet_in_db.attachments  # В модели 1:N это будет пустой список


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


# --- Тесты на создание твита с медиа (требуют загрузки файлов) ---

# Сначала нужно создать фикстуру для загрузки медиа
@pytest_asyncio.fixture(scope="function")
async def uploaded_media(authenticated_client: AsyncClient, db_session: AsyncSession) -> Media:
    """Загружает тестовый медиафайл и возвращает объект Media."""
    # Создаем "файл" в памяти
    file_content = b"this is a test image content"
    files = {"file": ("test_image.jpg", file_content, "image/jpeg")}
    response = await authenticated_client.post("/api/medias", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    media_id = json_response["media_id"]

    # Получаем объект Media из БД
    media = await db_session.get(Media, media_id)
    assert media is not None
    # Проверяем, что файл физически создался (если используется файловая система)
    # Для тестов с SQLite это менее актуально, но можно добавить проверку пути
    assert media.file_path.endswith(".jpg")
    # ВАЖНО: Убедимся, что tweet_id пока NULL
    assert media.tweet_id is None
    return media


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
    assert tweet_in_db.author_id == test_user.id

    # Проверяем медиа в БД
    await db_session.refresh(uploaded_media)  # Обновляем объект media
    assert uploaded_media.tweet_id == new_tweet_id  # Проверяем, что tweet_id установился

    # Проверяем связь через твит
    await db_session.refresh(tweet_in_db, attribute_names=['attachments'])  # Обновляем твит со связью
    assert len(tweet_in_db.attachments) == 1
    assert tweet_in_db.attachments[0].id == uploaded_media.id


async def test_create_tweet_with_nonexistent_media(
        authenticated_client: AsyncClient,
):
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


# TODO: Добавить тесты для создания твита с несколькими медиа
