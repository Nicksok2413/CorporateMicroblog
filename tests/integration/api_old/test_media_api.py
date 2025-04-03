"""Интеграционные тесты для API эндпоинта /medias."""

import io

import pytest
from httpx import AsyncClient
from fastapi import status

from app.models import User


@pytest.mark.asyncio
async def test_upload_media_success(async_client: AsyncClient, test_user_alice: User):
    """Тест успешной загрузки медиафайла (изображения)."""
    headers = {"api-key": test_user_alice.api_key}
    # Создаем фейковый файл в памяти
    file_content = b"fake image data"
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}

    response = await async_client.post("/api_old/v1/medias", files=files, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    json_response = response.json()
    assert json_response["result"] is True
    assert "media_id" in json_response
    assert isinstance(json_response["media_id"], int)
    # TODO: Можно добавить проверку, что файл действительно сохранен на диске (если не мокать файловую систему)
    # TODO: Можно добавить проверку, что запись появилась в БД


@pytest.mark.asyncio
async def test_upload_media_invalid_type(async_client: AsyncClient, test_user_alice: User):
    """Тест загрузки файла недопустимого типа (ошибка 400 или 422)."""
    headers = {"api-key": test_user_alice.api_key}
    file_content = b"this is plain text"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    response = await async_client.post("/api_old/v1/medias", files=files, headers=headers)

    # Ожидаем ошибку BadRequestError или MediaValidationError, которые дают 400
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    json_response = response.json()
    assert json_response["result"] is False
    assert json_response["error_type"] == "media_validation_error"  # Или "bad_request"
    assert "Недопустимый тип файла" in json_response["error_message"]


@pytest.mark.asyncio
async def test_upload_media_unauthorized(async_client: AsyncClient):
    """Тест загрузки медиа без ключа (ошибка 401)."""
    file_content = b"fake image data"
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}

    response = await async_client.post("/api_old/v1/medias", files=files)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# TODO: Добавить тест на превышение размера файла (если валидация размера реализована)
# TODO: Добавить тест на ошибку сохранения файла (сложно без мокирования)
