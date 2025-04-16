import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError  # Для имитации ошибок БД

from src.core.config import settings
from src.core.exceptions import BadRequestError, MediaValidationError
from src.models import Media
from src.repositories import MediaRepository
from src.schemas.media import MediaCreate
from src.services.media_service import MediaService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---
# Фикстура для мока MediaRepository
@pytest.fixture
def mock_media_repo() -> MagicMock:
    repo = MagicMock(spec=MediaRepository)
    repo.create = AsyncMock()
    repo.model = Media
    return repo


# Фикстура для создания экземпляра сервиса
@pytest.fixture
def media_service(mock_media_repo: MagicMock) -> MediaService:
    service = MediaService(repo=mock_media_repo)
    # Сохраняем мок для доступа в тестах
    service._mock_media_repo = mock_media_repo
    return service


# --- Тесты для save_media_file ---
# Мокируем aiofiles.open и asyncio.to_thread/os.remove

# @patch используем для мокирования встроенных функций/классов
@patch("aiofiles.open", new_callable=MagicMock)  # Мок асинхронного open
@patch("src.services.media_service.MediaService._generate_unique_filename")  # Мок генератора имен
async def test_save_media_file_success(
        mock_generate_filename: MagicMock,
        mock_aio_open: MagicMock,
        media_service: MediaService,
        mock_db_session: MagicMock,
        mock_media_repo: MagicMock,
        test_media_obj: Media,
):
    """Тест успешного сохранения медиафайла."""
    original_filename = "photo.jpg"
    unique_filename = "12345_abc.jpg"
    content_type = "image/jpeg"
    file_content = b"file data"

    # Настраиваем моки
    file_mock = MagicMock()
    file_mock.read.side_effect = [file_content, b""]  # Имитируем чтение
    mock_generate_filename.return_value = unique_filename  # Присваиваем имя

    # Настраиваем мок aiofiles.open для возврата асинхронного контекстного менеджера
    mock_file_ctx = AsyncMock()  # Контекстный менеджер
    mock_file_handle = AsyncMock()  # Файловый дескриптор
    mock_file_handle.write = AsyncMock()
    mock_file_ctx.__aenter__.return_value = mock_file_handle
    mock_aio_open.return_value = mock_file_ctx

    # Настраиваем мок репозитория
    mock_media_repo.create.return_value = test_media_obj  # Имитируем создание объекта Media

    # Вызываем метод сервиса
    saved_media = await media_service.save_media_file(
        db=mock_db_session,
        file=file_mock,
        filename=original_filename,
        content_type=content_type
    )

    # Проверки
    assert saved_media == test_media_obj
    mock_generate_filename.assert_called_once_with(original_filename)
    # Проверяем путь сохранения
    expected_save_path = settings.MEDIA_ROOT_PATH / unique_filename
    mock_aio_open.assert_called_once_with(expected_save_path, 'wb')
    mock_file_handle.write.assert_awaited_once_with(file_content)

    # Проверяем создание записи в БД
    expected_schema = MediaCreate(file_path=unique_filename)
    # Проверка, что вызов был
    mock_media_repo.create.assert_awaited_once()
    # Получаем аргументы последнего вызова
    last_call = mock_media_repo.create.await_args
    assert last_call is not None
    # Проверяем именованные аргументы
    assert 'db' in last_call.kwargs
    assert last_call.kwargs['db'] == mock_db_session
    assert 'obj_in' in last_call.kwargs
    assert isinstance(last_call.kwargs['obj_in'], MediaCreate)
    assert last_call.kwargs['obj_in'].model_dump() == expected_schema.model_dump()

    # Проверяем вызовы
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(test_media_obj)
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


@patch("src.services.media_service.MediaService._generate_unique_filename")
async def test_save_media_file_validation_error(
        mock_generate_filename: MagicMock,
        media_service: MediaService,
        mock_db_session: MagicMock,
):
    """Тест ошибки валидации типа файла."""
    original_filename = "doc.pdf"
    content_type = "application/pdf"

    # Настраиваем мок
    file_mock = MagicMock()

    # Проверяем, что выбрасывается MediaValidationError
    with pytest.raises(MediaValidationError) as exc_info:
        await media_service.save_media_file(
            db=mock_db_session, file=file_mock, filename=original_filename, content_type=content_type
        )

    assert f"Недопустимый тип файла '{content_type}'." in exc_info.value.detail

    # Проверяем, что другие методы не вызывались
    mock_generate_filename.assert_not_called()  # Не должны генерировать имя
    media_service._mock_media_repo.create.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()


@patch("aiofiles.open", new_callable=MagicMock)
@patch("src.services.media_service.MediaService._generate_unique_filename")
@patch("pathlib.Path.exists")  # Мокируем проверку существования файла
@patch("pathlib.Path.unlink")  # Мокируем удаление файла
async def test_save_media_file_io_error(
        mock_unlink: MagicMock,
        mock_exists: MagicMock,
        mock_generate_filename: MagicMock,
        mock_aio_open: MagicMock,
        media_service: MediaService,
        mock_db_session: MagicMock,
):
    """Тест ошибки при записи файла."""
    original_filename = "photo.jpg"
    unique_filename = "12345_abc.jpg"
    content_type = "image/jpeg"

    # Настраиваем моки
    file_mock = MagicMock()
    mock_generate_filename.return_value = unique_filename

    # Имитируем ошибку при входе в контекст через контекстный менеджер
    mock_file_ctx = AsyncMock()
    mock_file_ctx.__aenter__.side_effect = IOError("Disk full")  # Ошибка при __aenter__
    mock_aio_open.return_value = mock_file_ctx

    # Имитируем, что файл мог быть частично создан
    mock_exists.return_value = True

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError) as exc_info:
        await media_service.save_media_file(
            db=mock_db_session, file=file_mock, filename=original_filename, content_type=content_type
        )
    assert "Ошибка при сохранении файла" in exc_info.value.detail

    # Проверяем вызовы
    mock_generate_filename.assert_called_once()
    expected_save_path = settings.MEDIA_ROOT_PATH / unique_filename
    mock_aio_open.assert_called_once_with(expected_save_path, 'wb')
    # Проверяем попытку удаления файла
    mock_exists.assert_called_once()
    mock_unlink.assert_called_once_with(missing_ok=True)
    # БД не должна была изменяться
    media_service._mock_media_repo.create.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_not_awaited()  # Ошибка до транзакции БД


@patch("aiofiles.open", new_callable=MagicMock)
@patch("src.services.media_service.MediaService._generate_unique_filename")
@patch("pathlib.Path.exists")
@patch("pathlib.Path.unlink")
async def test_save_media_file_db_error(
        mock_unlink: MagicMock,
        mock_exists: MagicMock,
        mock_generate_filename: MagicMock,
        mock_aio_open: MagicMock,
        media_service: MediaService,
        mock_db_session: MagicMock,
        mock_media_repo: MagicMock,
):
    """Тест ошибки при записи в БД после сохранения файла."""
    original_filename = "photo.jpg"
    unique_filename = "12345_abc.jpg"
    content_type = "image/jpeg"
    file_content = b"file data"

    # Настраиваем моки
    file_mock = MagicMock()
    file_mock.read.side_effect = [file_content, b""]
    mock_generate_filename.return_value = unique_filename

    # Успешное сохранение файла
    mock_file_ctx = AsyncMock()
    mock_file_handle = AsyncMock()
    mock_file_handle.write = AsyncMock()
    mock_file_ctx.__aenter__.return_value = mock_file_handle
    mock_aio_open.return_value = mock_file_ctx

    # Ошибка при создании записи в БД
    mock_media_repo.create.side_effect = SQLAlchemyError("DB connection error")

    # Имитируем, что файл был создан
    mock_exists.return_value = True

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError) as exc_info:
        await media_service.save_media_file(
            db=mock_db_session, file=file_mock, filename=original_filename, content_type=content_type
        )

    assert "Ошибка при сохранении информации о медиафайле" in exc_info.value.detail

    # Проверяем вызовы
    mock_generate_filename.assert_called_once()
    mock_aio_open.assert_called_once()  # Файл пытались сохранить
    mock_media_repo.create.assert_awaited_once()  # Запись в БД пытались создать
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_awaited_once()  # Должен быть откат БД
    # Проверяем попытку удаления файла после ошибки БД
    mock_exists.assert_called_once()
    mock_unlink.assert_called_once_with(missing_ok=True)


# --- Тесты для delete_media_files ---

# Мокируем asyncio.to_thread и _delete_single_file_sync
@patch("asyncio.to_thread")
@patch("src.services.media_service.MediaService._delete_single_file_sync")
async def test_delete_media_files_success(
        mock_delete_sync: MagicMock,
        mock_to_thread: MagicMock,  # asyncio.to_thread сам по себе не async, но gather ждет его результат
        media_service: MediaService,
        caplog,
):
    """Тест успешного удаления нескольких файлов."""
    file_paths = ["path1.jpg", "path2.png"]

    # Имитируем успешное выполнение _delete_single_file_sync
    mock_delete_sync.return_value = True

    # Настраиваем to_thread, чтобы он возвращал результат вызова sync-функции
    # Имитируем awaitable поведение
    async def simple_wrapper(func, arg):
        return func(arg)

    mock_to_thread.side_effect = simple_wrapper

    # Запускаем метод и проверяем логи
    with caplog.at_level("INFO"):  # Устанавливаем уровень перед вызовом
        await media_service.delete_media_files(file_paths)

    # Проверяем количество вызовов
    assert mock_to_thread.call_count == 2
    assert mock_delete_sync.call_count == 2

    # Проверяем пути
    # expected_path1 = settings.MEDIA_ROOT_PATH / file_paths[0]
    # expected_path2 = settings.MEDIA_ROOT_PATH / file_paths[1]
    # # Проверяем, что sync-метод вызывался с правильными Path объектами
    # # (Замечание: проверка аргументов mock_delete_sync может быть сложной из-за lambda/to_thread,
    # # проще проверить call_count и логику внутри)
    # # Как вариант - проверить аргументы mock_to_thread
    # assert mock_to_thread.call_args_list[0][0][1] == expected_path1
    # assert mock_to_thread.call_args_list[1][0][1] == expected_path2

    # Проверки логов
    assert "Запуск удаления 2 физических медиафайлов..."  in caplog.text
    assert "Файл 'path1.jpg' успешно удален." in caplog.text
    assert "Файл 'path2.png' успешно удален." in caplog.text
    assert "Завершено удаление файлов: 2 успешно из 2." in caplog.text


@patch("asyncio.to_thread")
@patch("src.services.media_service.MediaService._delete_single_file_sync")
async def test_delete_media_files_one_fails(
        mock_delete_sync: MagicMock,
        mock_to_thread: MagicMock,
        media_service: MediaService,
        caplog,
):
    """Тест удаления, когда один файл не найден, а другой удаляется."""
    file_paths = ["found.jpg", "not_found.png"]

    # Настраиваем мок _delete_single_file_sync
    def delete_side_effect(path: Path):
        if "not_found" in str(path):
            # Возвращаем False для файла, который "не найден"
            return False
        else:
            # Возвращаем True для успешно удаленного
            return True

    mock_delete_sync.side_effect = delete_side_effect

    # Настраиваем мок to_thread
    async def simple_wrapper(func, arg):
        return func(arg)

    mock_to_thread.side_effect = simple_wrapper

    # Запускаем метод и проверяем логи
    with caplog.at_level("INFO"):  # Устанавливаем уровень
        await media_service.delete_media_files(file_paths)

    # Проверяем количество вызовов
    assert mock_to_thread.call_count == 2
    assert mock_delete_sync.call_count == 2

    # Проверяем логи
    assert "Запуск удаления 2 физических медиафайлов..."  in caplog.text
    assert "Завершено удаление файлов: 1 успешно из 2." in caplog.text

    # Проверяем лог WARNING о ненайденном файле (если логгер настроен на WARNING)
    with caplog.at_level("WARNING"):
        await media_service.delete_media_files(file_paths)  # Повторный вызов для другого уровня

    assert "Файл для синхронного удаления не найден" in caplog.text
    assert "not_found.png" in caplog.text


@patch("asyncio.to_thread")
@patch("src.services.media_service.MediaService._delete_single_file_sync")
async def test_delete_media_files_os_error(
        mock_delete_sync: MagicMock,
        mock_to_thread: MagicMock,
        media_service: MediaService,
        caplog,
):
    """Тест удаления, когда происходит ошибка ОС."""
    file_paths = ["error.jpg"]
    error_message = "Permission denied"

    # Настраиваем мок _delete_single_file_sync на выброс ошибки
    mock_delete_sync.side_effect = OSError(error_message)

    # Имитируем проброс исключения из to_thread
    async def error_wrapper(func, arg):
        try:
            return func(arg)
        except Exception as exc:
            raise exc

    mock_to_thread.side_effect = error_wrapper

    # Запускаем метод и проверяем логи
    with caplog.at_level("ERROR"):  # Устанавливаем уровень
        await media_service.delete_media_files(file_paths)

    # Проверяем количество вызовов
    assert mock_to_thread.call_count == 1
    assert mock_delete_sync.call_count == 1

    # Проверяем лог ошибки
    assert f"Ошибка при удалении файла '{file_paths[0]}': {error_message}" in caplog.text
    assert "Завершено удаление файлов: 0 успешно из 1." in caplog.text


# --- Тест для _delete_single_file_sync ---
# Этот метод синхронный, тестируем напрямую

@patch("os.remove")
def test_delete_single_file_sync_success(mock_os_remove: MagicMock, media_service: MediaService):
    """Тест успешного синхронного удаления."""
    file_path = Path("/fake/path/file.txt")

    # Вызываем метод сервиса
    result = media_service._delete_single_file_sync(file_path)

    # Проверки
    assert result is True
    mock_os_remove.assert_called_once_with(file_path)


@patch("os.remove")
def test_delete_single_file_sync_not_found(mock_os_remove: MagicMock, media_service: MediaService):
    """Тест синхронного удаления, когда файл не найден."""
    file_path = Path("/fake/path/notfound.txt")
    mock_os_remove.side_effect = FileNotFoundError

    # Вызываем метод сервиса
    result = media_service._delete_single_file_sync(file_path)

    # Проверки
    assert result is False
    mock_os_remove.assert_called_once_with(file_path)


@patch("os.remove")
def test_delete_single_file_sync_os_error(mock_os_remove: MagicMock, media_service: MediaService):
    """Тест синхронного удаления при ошибке ОС."""
    file_path = Path("/fake/path/protected.txt")
    mock_os_remove.side_effect = OSError("Permission denied")

    # Проверяем, что выбрасывается OSError
    with pytest.raises(OSError):
        media_service._delete_single_file_sync(file_path)

    # Проверяем вызов
    mock_os_remove.assert_called_once_with(file_path)


# --- Тест для get_media_url ---

def test_get_media_url(media_service: MediaService, test_media_obj: Media):
    """Тест генерации URL для медиа."""
    test_media_obj.file_path = "some/dir/image.jpg"
    expected_url = f"{settings.MEDIA_URL_PREFIX}/{test_media_obj.file_path}"

    # Вызываем метод сервиса
    url = media_service.get_media_url(test_media_obj)

    # Проверки
    assert url == expected_url


def test_get_media_url_with_slashes(media_service: MediaService, test_media_obj: Media):
    """Тест генерации URL с возможными лишними слешами в настройках/пути."""
    # Имитируем лишние слеши
    settings.MEDIA_URL_PREFIX = "/media/"  # Лишний слеш в конце
    test_media_obj.file_path = "/image.jpg"  # Лишний слеш в начале

    # Ожидаем корректный URL без двойных слешей
    expected_url = "/media/image.jpg"

    # Вызываем метод сервиса
    url = media_service.get_media_url(test_media_obj)

    # Проверки
    assert url == expected_url
    # Восстанавливаем настройку для других тестов (если scope фикстуры шире function)
    settings.MEDIA_URL_PREFIX = "/media"
