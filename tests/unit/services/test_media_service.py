"""Юнит-тесты для MediaService."""

import io
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from app.services.media_service import media_service
from app.models import Media
from app.schemas.media import MediaCreate
from app.core.exceptions import MediaValidationError, BadRequestError
from app.core.config import settings  # Нужен для пути сохранения


# Мокируем aiofiles.open, т.к. он используется для записи
@patch("app.services.media_service.aiofiles.open", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_save_media_service_success(mock_aio_open, mocker):
    """Тест успешного сохранения медиа."""
    mock_media_repo = mocker.patch("app.services.media_service.media_repo", autospec=True)

    # Настройка мока репозитория
    created_media = Media(id=1, file_path="some-uuid.jpg")
    mock_media_repo.create.return_value = created_media

    # Входные данные
    db_session_mock = AsyncMock()
    file_content = b"image data"
    file_obj = io.BytesIO(file_content)
    filename = "test.jpg"
    content_type = "image/jpeg"

    # Мок для uuid.uuid4(), чтобы имя файла было предсказуемым
    mocker.patch("app.services.media_service.uuid.uuid4", return_value="fixed-uuid")
    expected_filename = "fixed-uuid.jpg"
    expected_save_path = settings.STORAGE_PATH_OBJ / expected_filename

    # Вызов сервиса
    media = await media_service.save_media_file(
        db=db_session_mock, file=file_obj, filename=filename, content_type=content_type
    )

    # Проверки
    assert media == created_media

    # Проверка вызова aiofiles.open
    mock_aio_open.assert_called_once_with(expected_save_path, 'wb')
    # Проверка вызова записи в файл (внутри контекстного менеджера mock_aio_open)
    # Это немного сложнее, но можно проверить, что write был вызван
    mock_file_handle = mock_aio_open.return_value.__aenter__.return_value
    mock_file_handle.write.assert_called_once_with(file_content)

    # Проверка вызова репозитория
    mock_media_repo.create.assert_called_once()
    # Проверяем аргументы вызова create
    call_args, call_kwargs = mock_media_repo.create.call_args
    assert call_kwargs['db'] == db_session_mock
    assert isinstance(call_kwargs['obj_in'], MediaCreate)
    assert call_kwargs['obj_in'].file_path == expected_filename


@pytest.mark.asyncio
async def test_save_media_service_invalid_type(mocker):
    """Тест сохранения файла недопустимого типа."""
    mock_media_repo = mocker.patch("app.services.media_service.media_repo", autospec=True)
    # Мок Path.unlink на случай, если он будет вызван
    mocker.patch("pathlib.Path.unlink", return_value=None)

    db_session_mock = AsyncMock()
    file_obj = io.BytesIO(b"text data")
    filename = "test.txt"
    content_type = "text/plain"  # Недопустимый тип

    with pytest.raises(MediaValidationError) as exc_info:
        await media_service.save_media_file(
            db=db_session_mock, file=file_obj, filename=filename, content_type=content_type
        )

    assert "Недопустимый тип файла" in str(exc_info.value)
    mock_media_repo.create.assert_not_called()  # Запись в БД не должна вызываться

# TODO: Добавить тест на ошибку записи файла (мокируя aiofiles.open, чтобы он вызвал исключение)
# TODO: Добавить тест на ошибку создания записи в БД (мокируя repo.create)
