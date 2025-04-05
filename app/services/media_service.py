"""Сервис для работы с медиафайлами."""

from pathlib import Path
from random import choice
from string import ascii_lowercase, digits
from time import time
from typing import IO, Optional

import aiofiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, MediaValidationError
from app.core.logging import log
from app.models.media import Media
from app.repositories import MediaRepository
from app.schemas.media import MediaCreate
from app.services.base_service import BaseService


class MediaService(BaseService[Media, MediaRepository]):
    """
    Сервис для управления медиафайлами.

    Отвечает за сохранение файлов, создание записей в БД.
    Использует комбинацию timestamp + короткая случайная строка для имен файлов.
    """
    ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif"]
    RANDOM_PART_LENGTH = 6  # Длина случайной части имени файла

    async def _validate_file(self, filename: str, content_type: Optional[str]) -> None:
        """
        Валидирует загружаемый файл по типу.

        Args:
            filename: Имя файла.
            content_type: MIME-тип файла (опционально).

        Raises:
            MediaValidationError: Если тип файла не разрешен.
        """
        file_name_log = filename or "unknown"
        content_type_log = content_type or "unknown"
        log.debug(f"Валидация файла: name='{file_name_log}', type='{content_type_log}'")

        if not content_type or content_type not in self.ALLOWED_CONTENT_TYPES:
            msg = (f"Недопустимый тип файла '{content_type_log}'. "
                   f"Разрешены: {', '.join(self.ALLOWED_CONTENT_TYPES)}")
            log.warning(msg)
            raise MediaValidationError(detail=msg)

        log.debug(f"Файл '{file_name_log}' прошел валидацию.")

    def _generate_short_random_string(self, length: int = RANDOM_PART_LENGTH) -> str:
        """Генерирует короткую случайную строку из букв и цифр."""
        return ''.join(choice(ascii_lowercase + digits) for _ in range(length))

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        Генерирует уникальное имя файла на основе timestamp и случайной строки.

        Args:
            original_filename: Исходное имя файла.

        Returns:
            str: Уникальное имя файла формата <timestamp_us>_<random_chars>.<ext>.
                 Пример: 1678886400123456_a3x7p1.jpg
        """
        extension = Path(original_filename).suffix.lower() or ".unknown"
        # Время в микросекундах для большей уникальности
        timestamp_us = int(time() * 1_000_000)
        random_part = self._generate_short_random_string()
        unique_name = f"{timestamp_us}_{random_part}{extension}"
        log.debug(f"Сгенерировано уникальное имя файла: '{unique_name}' для '{original_filename}'")
        return unique_name

    async def save_media_file(
            self,
            db: AsyncSession,
            *,
            file: IO[bytes],
            filename: str,
            content_type: str
    ) -> Media:
        """
        Сохраняет медиафайл и создает соответствующую запись в БД.

        Args:
            db: Сессия БД.
            file: Файловый объект (из UploadFile.file).
            filename: Оригинальное имя файла.
            content_type: MIME-тип файла.

        Returns:
            Media: Созданный объект Media.

        Raises:
            MediaValidationError: При ошибке валидации файла.
            BadRequestError: При ошибке сохранения файла или записи в БД.
        """
        await self._validate_file(filename, content_type)

        unique_filename = self._generate_unique_filename(filename or "untitled")

        # Определяем путь для сохранения
        storage_dir = getattr(settings, 'EFFECTIVE_STORAGE_PATH_OBJ', settings.STORAGE_PATH_OBJ)

        if not storage_dir:
            log.error("Директория для сохранения медиа не определена в настройках!")
            raise BadRequestError("Ошибка конфигурации сервера: не настроено хранилище медиа.")

        if isinstance(storage_dir, str):
            storage_dir = Path(storage_dir)

        save_path = storage_dir / unique_filename
        # Путь, сохраняемый в БД - только имя файла (относительно storage_dir)
        relative_path = unique_filename

        log.info(f"Сохранение медиафайла '{filename}' как '{unique_filename}' в '{save_path}'")

        media: Optional[Media] = None

        try:
            # Этап 1: Сохранение файла
            try:
                # Асинхронная запись файла
                async with await aiofiles.open(save_path, 'wb') as out_file:
                    while content := file.read(1024 * 1024):  # Читаем по 1MB
                        if isinstance(content, bytes):
                            await out_file.write(content)
                        else:
                            raise TypeError("Ошибка чтения файла: ожидались байты.")

                log.success(f"Файл '{unique_filename}' успешно сохранен.")

            except (IOError, TypeError, Exception) as io_exc:
                log.error(f"Ошибка при сохранении файла '{unique_filename}': {io_exc}", exc_info=True)

                # Пытаемся удалить частично записанный файл
                if save_path.exists():
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError:
                        pass

                raise BadRequestError("Ошибка при сохранении файла.") from io_exc

            # Этап 2: Создание записи в БД (в транзакции)
            try:
                media_in = MediaCreate(file_path=relative_path)  # Сохраняем относительный путь
                media = await self.repo.create(db=db, obj_in=media_in)
                await db.commit()
                await db.refresh(media)
                log.info(f"Запись для медиа ID {media.id} (файл '{unique_filename}') создана в БД.")
                return media

            except SQLAlchemyError as db_exc:
                await db.rollback()  # Откат при ошибке БД
                log.error(f"Ошибка БД при создании записи Media для '{unique_filename}': {db_exc}", exc_info=True)

                # Если запись в БД не удалась, удаляем сохраненный файл
                if save_path.exists():
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError as unlink_err:
                        log.error(f"Не удалось удалить файл '{unique_filename}' после ошибки БД: {unlink_err}")

                raise BadRequestError("Ошибка при сохранении информации о медиафайле.") from db_exc

        except Exception as outer_exc:
            log.exception(f"Непредвиденная внешняя ошибка при сохранении медиа {filename}: {outer_exc}")
            await db.rollback()  # Гарантируем откат, если транзакция была начата

            # Попытка удалить файл, если он существует
            if save_path.exists():
                try:
                    save_path.unlink(missing_ok=True)
                except OSError:
                    pass

            raise BadRequestError("Общая ошибка при сохранении медиа.") from outer_exc

    def get_media_url(self, media: Media) -> str:
        """
        Генерирует URL для доступа к медиафайлу.

        Args:
            media: Объект Media.

        Returns:
            str: Полный URL медиафайла.
        """
        # Убираем / с конца префикса и начала пути файла, если они есть, чтобы избежать двойного //
        url = f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/{media.file_path.lstrip('/')}"
        log.debug(f"Сгенерирован URL для медиа ID {media.id}: {url}")
        return url
