# tests/integration/test_media_api.py
import io

import pytest
from httpx import AsyncClient
from fastapi import status

# Маркер для всех тестов в этом файле
pytestmark = pytest.mark.asyncio


# --- Тесты для POST /api/v1/media ---

async def test_upload_media_success_jpeg(client: AsyncClient, auth_headers_user1: dict):
    file_content = b"fake jpeg data"
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
    response = await client.post("/api/v1/media", files=files, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True
    assert "media_id" in data
    assert isinstance(data["media_id"], int)
    # TODO: Add check if file actually saved in storage (requires setup)


async def test_upload_media_success_png(client: AsyncClient, auth_headers_user1: dict):
    file_content = b"fake png data"
    files = {"file": ("test.png", io.BytesIO(file_content), "image/png")}
    response = await client.post("/api/v1/media", files=files, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["result"] is True
    assert isinstance(data["media_id"], int)


async def test_upload_media_unsupported_type(client: AsyncClient, auth_headers_user1: dict):
    file_content = b"fake text data"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    response = await client.post("/api/v1/media", files=files, headers=auth_headers_user1)
    assert response.status_code == status.HTTP_400_BAD_REQUEST  # Or 422 if validation is stricter
    data = response.json()
    assert data["result"] is False
    assert data["error_type"] == "media_validation_error"  # Based on MediaService exception
    assert "Недопустимый тип файла" in data["error_message"]


async def test_upload_media_no_file(client: AsyncClient, auth_headers_user1: dict):
    response = await client.post("/api/v1/media", headers=auth_headers_user1)  # No files payload
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # FastAPI validation


async def test_upload_media_unauthorized(client: AsyncClient):
    file_content = b"fake jpeg data"
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
    response = await client.post("/api/v1/media", files=files)  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_upload_media_invalid_key(client: AsyncClient):
    file_content = b"fake jpeg data"
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
    headers = {"api-key": "invalidkey"}
    response = await client.post("/api/v1/media", files=files, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
