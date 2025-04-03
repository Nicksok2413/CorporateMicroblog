# tests/unit/test_media_service.py
import pytest
import io
from pathlib import Path
from unittest.mock import patch, AsyncMock  # Import mock tools

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import media_service
from app.models import Media
from app.core.exceptions import MediaValidationError, BadRequestError
from app.core.config import settings
from app.repositories import media_repo  # To potentially mock repo methods

# Маркер
pytestmark = pytest.mark.asyncio


# --- Тесты для MediaService._validate_file (косвенно или прямо) ---

async def test_validate_file_allowed_type(db_session: AsyncSession):
    # Этот тест больше проверяет отсутствие ошибки при валидном типе
    # В save_media_file происходит вызов _validate_file
    file_content = b"data"
    filename = "image.jpg"
    content_type = "image/jpeg"
    # Mock aiofiles.open and media_repo.create to isolate validation
    with patch('aiofiles.open', new_callable=AsyncMock) as mock_open, \
            patch.object(media_repo, 'create', new_callable=AsyncMock) as mock_create:
        # Mock the behavior of repo.create to return a dummy Media object
        mock_create.return_value = Media(id=1, file_path="some_path.jpg")
        try:
            await media_service.save_media_file(
                db=db_session,
                file=io.BytesIO(file_content),
                filename=filename,
                content_type=content_type
            )
        except MediaValidationError:
            pytest.fail("MediaValidationError raised unexpectedly for allowed type")
        # Assert _validate_file logic passed (no exception)


async def test_validate_file_disallowed_type():
    # Прямой тест для _validate_file может быть проще, если сделать его не приватным
    # или тестировать через save_media_file
    file_content = b"data"
    filename = "document.txt"
    content_type = "text/plain"
    with pytest.raises(MediaValidationError) as excinfo:
        # Вызываем save_media_file, который вызовет _validate_file
        await media_service.save_media_file(
            db=AsyncMock(),  # Mock DB session
            file=io.BytesIO(file_content),
            filename=filename,
            content_type=content_type
        )
    assert "Недопустимый тип файла 'text/plain'" in str(excinfo.value)


# --- Тесты для MediaService._generate_unique_filename ---

def test_generate_unique_filename():
    original_name = "MyPhoto.JPEG"
    unique_name = media_service._generate_unique_filename(original_name)
    assert unique_name != original_name
    assert unique_name.endswith(".jpeg")  # Check lowercase extension
    assert len(unique_name) > 36  # UUID + .ext


def test_generate_unique_filename_no_extension():
    original_name = "FileWithoutExtension"
    unique_name = media_service._generate_unique_filename(original_name)
    assert unique_name != original_name
    assert "." not in unique_name  # Expect no extension if original had none
    assert len(unique_name) == 36  # Just UUID


# --- Тесты для MediaService.save_media_file ---

async def test_save_media_file_success(db_session: AsyncSession):
    file_content = b"fake jpeg data bytes"
    filename = "photo.jpg"
    content_type = "image/jpeg"
    expected_media_id = 1

    # Mock aiofiles.open to simulate file writing
    # Mock media_repo.create to simulate DB insertion
    with patch('aiofiles.open', new_callable=AsyncMock) as mock_aio_open, \
            patch.object(media_repo, 'create', new_callable=AsyncMock) as mock_create:
        # Configure mock_create to return a Media object when called
        mock_create.return_value = Media(id=expected_media_id, file_path="dummy_uuid.jpg")

        media = await media_service.save_media_file(
            db=db_session,
            file=io.BytesIO(file_content),
            filename=filename,
            content_type=content_type
        )

        # Assertions
        mock_aio_open.assert_called_once()  # Check if file open was attempted
        # Check if called with a path ending in .jpg inside STORAGE_PATH_OBJ
        call_args, _ = mock_aio_open.call_args
        save_path = call_args[0]
        assert isinstance(save_path, Path)
        assert save_path.parent == settings.STORAGE_PATH_OBJ
        assert save_path.name.endswith(".jpg")

        mock_create.assert_called_once()  # Check if repo create was called
        # Check the data passed to repo.create (relative path)
        create_call_args, _ = mock_create.call_args
        created_obj_in = create_call_args.kwargs.get('obj_in')
        assert created_obj_in is not None
        assert created_obj_in.file_path == save_path.name  # Should be just the filename

        assert media is not None
        assert media.id == expected_media_id


async def test_save_media_file_io_error(db_session: AsyncSession):
    file_content = b"data"
    filename = "photo.png"
    content_type = "image/png"

    # Mock aiofiles.open to raise an IOError
    with patch('aiofiles.open', new_callable=AsyncMock) as mock_aio_open, \
            patch('pathlib.Path.unlink') as mock_unlink, \
            patch('pathlib.Path.exists') as mock_exists:  # Mock unlink and exists
        mock_aio_open.side_effect = IOError("Disk full")
        mock_exists.return_value = True  # Assume file was partially created

        with pytest.raises(BadRequestError) as excinfo:
            await media_service.save_media_file(
                db=db_session,
                file=io.BytesIO(file_content),
                filename=filename,
                content_type=content_type
            )

        assert "Ошибка при сохранении файла" in str(excinfo.value)
        mock_exists.assert_called_once()  # Check if existence check was done
        mock_unlink.assert_called_once()  # Check if cleanup was attempted


async def test_save_media_file_db_error(db_session: AsyncSession):
    file_content = b"data"
    filename = "photo.gif"
    content_type = "image/gif"

    # Mock repo.create to raise an exception
    # Mock aiofiles.open to succeed
    with patch('aiofiles.open', new_callable=AsyncMock) as mock_aio_open, \
            patch.object(media_repo, 'create', new_callable=AsyncMock) as mock_create, \
            patch('pathlib.Path.unlink') as mock_unlink, \
            patch('pathlib.Path.exists') as mock_exists:  # Mock unlink and exists

        mock_create.side_effect = Exception("DB connection error")
        mock_exists.return_value = True  # Assume file was created

        with pytest.raises(BadRequestError) as excinfo:
            await media_service.save_media_file(
                db=db_session,
                file=io.BytesIO(file_content),
                filename=filename,
                content_type=content_type
            )

        assert "Ошибка при сохранении информации о медиафайле" in str(excinfo.value)
        mock_aio_open.assert_called_once()  # File writing should have succeeded
        mock_create.assert_called_once()  # DB create attempt
        mock_exists.assert_called_once()  # Check for file existence for cleanup
        mock_unlink.assert_called_once()  # Check if cleanup was attempted


# --- Тесты для MediaService.get_media_url ---

def test_get_media_url_success(test_media: Media, settings):
    settings.MEDIA_URL_PREFIX = "/static/media"  # Ensure prefix is set for test
    expected_url = f"/static/media/{test_media.file_path}"
    actual_url = media_service.get_media_url(test_media)
    assert actual_url == expected_url


def test_get_media_url_with_slashes(settings):
    settings.MEDIA_URL_PREFIX = "/static/media/"  # Trailing slash
    media = Media(id=2, file_path="/leading_slash.png")  # Leading slash
    expected_url = "/static/media/leading_slash.png"  # Should handle slashes correctly
    actual_url = media_service.get_media_url(media)
    assert actual_url == expected_url


def test_get_media_url_prefix_not_set(test_media: Media, settings):
    settings.MEDIA_URL_PREFIX = ""  # Simulate prefix not set
    actual_url = media_service.get_media_url(test_media)
    assert actual_url == ""  # Expect empty string or handle as error
