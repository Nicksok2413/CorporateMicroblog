import io
import pytest
from httpx import AsyncClient
from fastapi import status

from src.core.config import settings
from src.models import User, Media  # Нужны для проверок и типизации
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


# === POST /api/media ===

async def test_upload_media_unauthorized(client: AsyncClient):
    files = {'file': ('image.jpg', b'fake image data', 'image/jpeg')}
    response = await client.post("/api/media", files=files)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Генерируем "картинки" разного типа
@pytest.mark.parametrize("filename, content_type, content", [
    ("test.jpg", "image/jpeg", b"fake jpeg"),
    ("test.png", "image/png", b"fake png"),
    ("test.gif", "image/gif", b"fake gif"),
])
async def test_upload_media_success(authenticated_client: AsyncClient, db_session: AsyncSession, filename, content_type,
                                    content):
    files = {'file': (filename, io.BytesIO(content), content_type)}  # Используем BytesIO
    response = await authenticated_client.post("/api/media", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    assert "media_id" in json_response
    media_id = json_response["media_id"]
    assert isinstance(media_id, int)
    assert media_id > 0

    # Проверяем запись в БД
    media = await db_session.get(Media, media_id)
    assert media is not None
    assert media.id == media_id
    assert media.file_path.endswith(filename.split('.')[-1])  # Проверяем расширение
    assert media.tweet_id is None  # Медиа еще не привязано

    # TODO: Проверить, что файл реально сохранен (если настроено монтирование)
    # Это сложнее в автоматическом тесте, но можно проверить в dev режиме


async def test_upload_media_invalid_type(authenticated_client: AsyncClient):
    files = {'file': ('document.txt', b'some text', 'text/plain')}
    response = await authenticated_client.post("/api/media", files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST  # MediaValidationError
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "media_validation_error"
    assert "Недопустимый тип файла" in json_response["error_message"]


async def test_upload_media_no_file(authenticated_client: AsyncClient):
    # Отправляем форму без файла 'file'
    response = await authenticated_client.post("/api/media")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # Ошибка валидации FastAPI
