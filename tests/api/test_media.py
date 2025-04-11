# tests/api/test_media.py
import io
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Media, User  # Импортируем модели
from src.schemas.media import MediaCreateResult  # Схемы для проверок

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Тесты загрузки медиа ---

async def test_upload_media_success_jpeg(
        async_client: AsyncClient,
        nick_headers: dict,
        db_session: AsyncSession,
):
    """Тест успешной загрузки jpeg файла."""
    # Создаем имитацию файла в памяти
    file_content = b"fake jpeg data"
    file_obj = io.BytesIO(file_content)
    file_obj.name = "test.jpg"  # httpx может использовать имя файла

    files = {"file": (file_obj.name, file_obj, "image/jpeg")}

    response = await async_client.post("/api/media", files=files, headers=nick_headers)

    assert response.status_code == status.HTTP_201_CREATED
    data = MediaCreateResult(**response.json())
    assert data.result is True
    assert isinstance(data.media_id, int)

    # Проверяем, что запись создана в БД
    media_db = await db_session.get(Media, data.media_id)
    assert media_db is not None
    assert media_db.id == data.media_id
    assert media_db.file_path.endswith(".jpg")  # Проверяем расширение в имени файла

    # Тут можно было бы проверить и сохранение файла на диск,
    # но это выходит за рамки API теста и усложнит его.
    # Достаточно проверить, что сервис отработал и вернул ID.


async def test_upload_media_success_png(
        async_client: AsyncClient,
        nick_headers: dict,
        db_session: AsyncSession,
):
    """Тест успешной загрузки png файла."""
    file_content = b"fake png data"
    file_obj = io.BytesIO(file_content)

    files = {"file": ("test.png", file_obj, "image/png")}  # Указываем имя и тип

    response = await async_client.post("/api/media", files=files, headers=nick_headers)

    assert response.status_code == status.HTTP_201_CREATED
    data = MediaCreateResult(**response.json())
    assert data.result is True
    assert isinstance(data.media_id, int)

    media_db = await db_session.get(Media, data.media_id)
    assert media_db is not None
    assert media_db.file_path.endswith(".png")


async def test_upload_media_invalid_content_type(
        async_client: AsyncClient,
        nick_headers: dict,
):
    """Тест загрузки файла с неразрешенным типом контента."""
    file_content = b"some text data"
    file_obj = io.BytesIO(file_content)

    files = {"file": ("test.txt", file_obj, "text/plain")}  # Неразрешенный тип

    response = await async_client.post("/api/media", files=files, headers=nick_headers)

    # Ожидаем ошибку валидации от сервиса, которая преобразуется в 400
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "media_validation_error"
    assert "Недопустимый тип файла" in data["error_message"]


async def test_upload_media_no_file(
        async_client: AsyncClient,
        nick_headers: dict,
):
    """Тест отправки формы без файла."""
    # Отправляем запрос без параметра 'files'
    response = await async_client.post("/api/media", headers=nick_headers)

    # FastAPI вернет ошибку валидации запроса, т.к. поле 'file' обязательное
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    # Формат ошибки валидации FastAPI отличается от наших кастомных
    assert "detail" in data
    assert any("Field required" in detail["msg"] for detail in data["detail"])


async def test_upload_media_unauthorized(async_client: AsyncClient):
    """Тест загрузки файла без авторизации."""
    file_content = b"fake jpeg data"
    file_obj = io.BytesIO(file_content)
    files = {"file": ("test.jpg", file_obj, "image/jpeg")}

    response = await async_client.post("/api/media", files=files)  # Без заголовка

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "unauthorized"
