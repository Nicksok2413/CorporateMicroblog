from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile

from src.api.routes.media import upload_media_file
from src.models import Media, User
from src.schemas.media import MediaCreateResult

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---

# Фикстура для мока UploadFile
@pytest.fixture
def mock_upload_file() -> MagicMock:
    upload_file = MagicMock(spec=UploadFile)
    upload_file.filename = "test.jpg"
    upload_file.content_type = "image/jpeg"
    file_obj = MagicMock()  # Мокируем файловый объект внутри UploadFile
    upload_file.file = file_obj
    upload_file.close = AsyncMock()
    return upload_file


# --- Тест для обработчика роута upload_media_file ---

async def test_upload_media_file_handler_success(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_media_service: MagicMock,
        mock_upload_file: MagicMock,
):
    """Юнит-тест для функции обработчика upload_media_file - успешный случай."""
    # Настраиваем мок сервиса на возврат успешного результата
    media_id = 123
    saved_media_mock = MagicMock(spec=Media)
    saved_media_mock.id = media_id
    mock_media_service.save_media_file.return_value = saved_media_mock

    # Вызываем сам обработчик роута с моками вместо реальных зависимостей
    result = await upload_media_file(
        db=mock_db_session,
        current_user=test_user_obj,
        media_service=mock_media_service,
        file=mock_upload_file,
    )

    # Проверяем, что save_media_file был вызван с правильными аргументами
    mock_media_service.save_media_file.assert_awaited_once_with(
        db=mock_db_session,
        file=mock_upload_file.file,
        filename=mock_upload_file.filename,
        content_type=mock_upload_file.content_type,
    )

    # Проверяем, что file.close был вызван
    mock_upload_file.close.assert_awaited_once()

    # Проверяем возвращаемый результат
    assert isinstance(result, MediaCreateResult)
    assert result.media_id == media_id


async def test_upload_media_file_handler_service_exception(
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_media_service: MagicMock,
        mock_upload_file: MagicMock,
):
    """Юнит-тест для функции обработчика upload_media_file - ошибка в сервисе."""
    # Настраиваем мок сервиса на выброс исключения
    error_message = "Service error"
    mock_media_service.save_media_file.side_effect = Exception(error_message)

    # Проверяем, что исключение пробрасывается дальше
    with pytest.raises(Exception, match=error_message):
        await upload_media_file(
            db=mock_db_session,
            current_user=test_user_obj,
            media_service=mock_media_service,
            file=mock_upload_file,
        )

    # Проверяем, что save_media_file был вызван
    mock_media_service.save_media_file.assert_awaited_once()
    # Проверяем, что file.close был вызван в блоке finally
    mock_upload_file.close.assert_awaited_once()
