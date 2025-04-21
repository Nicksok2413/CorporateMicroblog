import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models import Media

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тесты для POST /api/medias ---

async def test_upload_media_unauthorized(client: AsyncClient):
    """Тест загрузки медиа без авторизации."""
    files = {"file": ("test.jpg", b"content", "image/jpeg")}
    response = await client.post("/api/medias", files=files)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_upload_media_invalid_key(client: AsyncClient):
    """Тест загрузки медиа с неверным ключом."""
    headers = {settings.API_KEY_HEADER: "invalid-key"}
    files = {"file": ("test.jpg", b"content", "image/jpeg")}
    response = await client.post("/api/medias", files=files, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_upload_media_success(
        authenticated_client: AsyncClient, db_session: AsyncSession
):
    """Тест успешной загрузки медиафайла."""
    filename = "test_image.png"
    file_content = "test content".encode()
    content_type = "image/png"
    files = {"file": (filename, file_content, content_type)}

    response = await authenticated_client.post("/api/medias", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    assert "media_id" in json_response
    media_id = json_response["media_id"]
    assert isinstance(media_id, int)
    assert media_id > 0

    # Проверяем запись в БД
    media_in_db: Media | None = await db_session.get(Media, media_id)
    assert media_in_db is not None
    assert media_in_db.tweet_id is None  # Должен быть не привязан
    assert media_in_db.file_path is not None
    assert media_in_db.file_path.endswith(".png")  # Проверяем расширение
    assert media_in_db.file_path.endswith(filename.split('.')[-1])

    # Проверяем, что файл создан во временной директории
    media_full_path = settings.MEDIA_ROOT_PATH / media_in_db.file_path
    assert media_full_path.exists()


async def test_upload_media_invalid_content_type(authenticated_client: AsyncClient):
    """Тест загрузки файла с неразрешенным типом контента."""
    filename = "mydoc.pdf"
    file_content = b"%PDF-1.4 test content"
    content_type = "application/pdf"
    files = {"file": (filename, file_content, content_type)}

    response = await authenticated_client.post("/api/medias", files=files)

    # Сервис должен вернуть MediaValidationError, который обрабатывается как 400 Bad Request
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "media_validation_error"
    assert "Недопустимый тип файла 'application/pdf'" in json_response["error_message"]


async def test_upload_media_no_file(authenticated_client: AsyncClient):
    """Тест запроса на загрузку медиа без прикрепленного файла."""
    # Отправляем запрос без 'files'
    response = await authenticated_client.post("/api/medias")

    # Ожидаем 422 с нашим кастомным форматом ответа
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    json_response = response.json()

    # Проверяем структуру ответа из нашего validation_exception_handler
    assert json_response["result"] is False
    assert json_response["error_type"] == "Validation Error"
    assert "error_message" in json_response
    assert "Поле 'body -> file': Field required" in json_response["error_message"]
