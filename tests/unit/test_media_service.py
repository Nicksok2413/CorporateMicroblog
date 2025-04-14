from unittest.mock import MagicMock  # Используем стандартный mock

import pytest

# Импортируем класс сервиса, который хотим протестировать
from src.services.media_service import MediaService
# Импортируем нужные исключения
from src.core.exceptions import MediaValidationError


# --- Фикстура для создания экземпляра сервиса ---
# (Репозиторий здесь не используется, поэтому можно передать mock или None)
@pytest.fixture
def media_service() -> MediaService:
    """Создает экземпляр MediaService для юнит-тестов."""
    # MediaRepository здесь не нужен для тестируемых методов, передаем mock
    mock_repo = MagicMock()
    return MediaService(repo=mock_repo)


# --- Тесты для _validate_file ---

def test_validate_file_success(media_service: MediaService):
    """Тест успешной валидации разрешенного типа файла."""
    # Не должно вызывать исключений
    media_service._validate_file("image.jpg", "image/jpeg")
    media_service._validate_file("image.png", "image/png")
    media_service._validate_file("image.gif", "image/gif")


def test_validate_file_failure(media_service: MediaService):
    """Тест валидации запрещенного типа файла."""
    with pytest.raises(MediaValidationError) as exc_info:
        media_service._validate_file("document.pdf", "application/pdf")
    assert "Недопустимый тип файла" in str(exc_info.value.detail)

    with pytest.raises(MediaValidationError):
        media_service._validate_file("archive.zip", "application/zip")


# --- Тесты для _generate_unique_filename ---

def test_generate_unique_filename_format(media_service: MediaService):
    """Тест формата генерируемого имени файла."""
    original_filename = "MyPhoto.JPG"
    unique_name = media_service._generate_unique_filename(original_filename)

    # Проверяем, что имя имеет формат timestamp_random.ext
    parts = unique_name.split('_')
    assert len(parts) == 2
    assert parts[0].isdigit()  # Первая часть - timestamp
    assert parts[1].endswith(".jpg")  # Заканчивается правильным расширением (в нижнем регистре)

    random_part = parts[1][:-4]  # Убираем расширение
    # Проверяем длину случайной части (по умолчанию 6)
    assert len(random_part) == media_service.RANDOM_PART_LENGTH
    # Проверяем, что случайная часть состоит из букв/цифр
    assert all(c.isalnum() for c in random_part)


def test_generate_unique_filename_uniqueness(media_service: MediaService):
    """Тест на уникальность (вероятностный)."""
    filenames = {media_service._generate_unique_filename("test.png") for _ in range(100)}
    # Вероятность коллизии при timestamp + 6 символах очень мала
    assert len(filenames) == 100

# TODO: Добавить юнит-тесты для save_media_file (потребуется мокинг aiofiles и репозитория)
# TODO: Добавить юнит-тесты для delete_media_files (потребуется мокинг os.remove/asyncio.to_thread)
