"""Сервис для работы с медиафайлами."""
import uuid
from pathlib import Path
from typing import IO, Optional

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, MediaValidationError
from app.core.logging import log
from app.models.media import Media
from app.repositories import media_repo
from app.schemas.media import MediaCreate
from app.services.base_service import BaseService


class MediaService(BaseService[Media, type(media_repo)]):
    """
    Сервис для управления медиафайлами.

    Отвечает за сохранение файлов, создание записей в БД.
    """
    ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif"]
    MAX_FILE_SIZE_MB = 10  # Максимальный размер файла в мегабайтах

    async def _validate_file(self, file: IO[bytes], filename: str, content_type: str):
        """
        Валидирует загружаемый файл по типу и размеру.

        Args:
            file: Файловый объект (из UploadFile).
            filename: Имя файла.
            content_type: MIME-тип файла.

        Raises:
            MediaValidationError: Если тип файла не разрешен или размер превышен.
        """
        log.debug(f"Валидация файла: name='{filename}', type='{content_type}'")
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            msg = f"Недопустимый тип файла '{content_type}'. Разрешены: {', '.join(self.ALLOWED_CONTENT_TYPES)}"
            log.warning(msg)
            raise MediaValidationError(detail=msg)

        log.debug(f"Файл '{filename}' прошел валидацию.")

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        Генерирует уникальное имя файла, сохраняя расширение.

        Args:
            original_filename: Исходное имя файла.

        Returns:
            str: Уникальное имя файла.
        """
        extension = Path(original_filename).suffix.lower()
        # Генерируем UUID и добавляем расширение
        unique_name = f"{uuid.uuid4()}{extension}"
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
        await self._validate_file(file, filename, content_type)

        unique_filename = self._generate_unique_filename(filename)
        save_path = settings.STORAGE_PATH_OBJ / unique_filename
        relative_path = unique_filename  # Путь для сохранения в БД

        log.info(f"Сохранение медиафайла '{filename}' как '{unique_filename}' в '{save_path}'")

        try:
            # Асинхронная запись файла
            async with aiofiles.open(save_path, 'wb') as out_file:
                while content := file.read(1024 * 1024):  # Читаем по 1MB
                    await out_file.write(content)
            log.success(f"Файл '{unique_filename}' успешно сохранен.")
        except Exception as e:
            log.error(f"Ошибка при сохранении файла '{unique_filename}': {e}", exc_info=True)
            # Попытка удалить частично сохраненный файл, если он есть
            if save_path.exists():
                try:
                    save_path.unlink()
                    log.info(f"Удален частично сохраненный файл '{unique_filename}'.")
                except OSError as unlink_err:
                    log.error(f"Не удалось удалить частично сохраненный файл '{unique_filename}': {unlink_err}")
            raise BadRequestError("Ошибка при сохранении файла.") from e

        # Создаем запись в БД
        try:
            media_in = MediaCreate(file_path=relative_path)
            media = await self.repo.create(db=db, obj_in=media_in)
            log.info(f"Запись для медиа ID {media.id} (файл '{unique_filename}') создана в БД.")
            return media
        except Exception as e:
            log.error(f"Ошибка при создании записи Media в БД для файла '{unique_filename}': {e}", exc_info=True)
            # Если запись в БД не удалась, удаляем сохраненный файл
            if save_path.exists():
                try:
                    save_path.unlink()
                    log.info(f"Удален файл '{unique_filename}', т.к. не удалось создать запись в БД.")
                except OSError as unlink_err:
                    log.error(f"Не удалось удалить файл '{unique_filename}' после ошибки БД: {unlink_err}")
            raise BadRequestError("Ошибка при сохранении информации о медиафайле.") from e

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

    async def get_media_by_id(self, db: AsyncSession, media_id: int) -> Optional[Media]:
        """
        Получает медиа по ID.

        Args:
            db: Сессия БД.
            media_id: ID медиа.

        Returns:
            Найденный медиафайл или None.
        """
        return await self.repo.get(db, media_id)


# Создаем экземпляр сервиса
media_service = MediaService(media_repo)
