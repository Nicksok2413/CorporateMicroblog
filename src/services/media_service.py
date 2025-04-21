"""Сервис для работы с медиафайлами."""

import asyncio
import os
from pathlib import Path
from random import choice
from string import ascii_lowercase, digits
from time import time
from typing import IO, List, Optional

import aiofiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BadRequestError, MediaValidationError
from src.core.logging import log
from src.models.media import Media
from src.repositories.media import MediaRepository
from src.schemas.media import MediaCreate
from src.services.base_service import BaseService


class MediaService(BaseService[Media, MediaRepository]):
    """
    Сервис для управления медиафайлами.

    Отвечает за сохранение файлов, создание записей в БД.
    Использует комбинацию timestamp + короткая случайная строка для имен файлов.
    """

    # Разрешенные типы контента для загружаемых медиа
    ALLOWED_CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/gif"}
    # Длина случайной части имени файла
    RANDOM_PART_LENGTH: int = 6

    async def _validate_file(self, filename: str, content_type: str) -> None:
        """
        Валидирует загружаемый файл по типу.

        Args:
            filename (str): Имя файла.
            content_type (str): MIME-type файла.

        Raises:
            MediaValidationError: Если тип файла не разрешен.
        """
        log.debug(f"Валидация файла: name='{filename}', type='{content_type}'")

        if content_type not in self.ALLOWED_CONTENT_TYPES:
            msg = (
                f"Недопустимый тип файла '{content_type}'. "
                f"Разрешены: {', '.join(self.ALLOWED_CONTENT_TYPES)}"
            )
            log.warning(msg)
            raise MediaValidationError(detail=msg)

        log.debug(f"Файл '{filename}' прошел валидацию.")

    def _generate_short_random_string(self, length: int = RANDOM_PART_LENGTH) -> str:
        """
        Генерирует короткую случайную строку из букв и цифр.

        Args:
            length (int): Желаемая длина генерируемой строки. По умолчанию используется значение `RANDOM_PART_LENGTH`.

        Returns:
            str: Случайная строка из строчных букв ASCII и цифр указанной длины.
        """
        return "".join(choice(ascii_lowercase + digits) for _ in range(length))

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        Генерирует уникальное имя файла на основе timestamp и случайной строки.

        Args:
            original_filename (str): Исходное имя файла.

        Returns:
            str: Уникальное имя файла формата <timestamp>_<random_chars>.<ext>.
                 Пример: 1678886400123456_a3x7p1.jpg
        """
        # Время в микросекундах для большей уникальности
        timestamp = int(time() * 1_000_000)
        random_part = self._generate_short_random_string()
        extension = Path(original_filename).suffix.lower()
        unique_name = f"{timestamp}_{random_part}{extension}"
        log.debug(
            f"Сгенерировано уникальное имя файла: '{unique_name}' для '{original_filename}'"
        )
        return unique_name

    async def save_media_file(
        self, db: AsyncSession, *, file: IO[bytes], filename: str, content_type: str
    ) -> Media:
        """
        Сохраняет медиафайл и создает соответствующую запись в БД.

        Args:
            db (AsyncSession): Сессия БД.
            file (IO[bytes]): Файловый объект.
            filename (str): Оригинальное имя файла.
            content_type (str): MIME-type файла.

        Returns:
            Media: Созданный объект Media.

        Raises:
            MediaValidationError: При ошибке валидации файла.
            BadRequestError: При ошибке сохранения файла или записи в БД.
        """
        media: Optional[Media] = None
        save_path: Optional[Path] = None

        try:
            await self._validate_file(filename, content_type)

            unique_filename: str = self._generate_unique_filename(filename)
            save_path = settings.MEDIA_ROOT_PATH / unique_filename  # type: ignore[operator]
            log.info(
                f"Сохранение медиафайла '{filename}' как '{unique_filename}' в '{save_path}'"
            )

            # Этап 1: Сохранение файла
            try:
                assert isinstance(save_path, Path), (
                    f"save_path должен быть Path, но получен {type(save_path)}"
                )

                async with aiofiles.open(save_path, "wb") as out_file:
                    while content := file.read(1024 * 1024):  # Читаем по 1MB
                        await out_file.write(content)
                log.success(f"Файл '{unique_filename}' успешно сохранен.")

            except (IOError, TypeError) as io_exc:
                log.error(
                    f"Ошибка при сохранении файла '{unique_filename}': {io_exc}",
                    exc_info=True,
                )
                # Пытаемся удалить частично записанный файл
                if save_path and save_path.exists():
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                raise BadRequestError("Ошибка при сохранении файла.") from io_exc

            # Этап 2: Создание записи в БД
            try:
                media_in = MediaCreate(file_path=unique_filename)
                media = await self.repo.create(db=db, obj_in=media_in)
                await db.commit()
                await db.refresh(media)
                log.info(
                    f"Запись для медиа ID {media.id} (файл '{unique_filename}') создана в БД."
                )
                return media

            except SQLAlchemyError as db_exc:
                await db.rollback()
                log.error(
                    f"Ошибка БД при создании записи Media для '{unique_filename}': {db_exc}",
                    exc_info=True,
                )
                # Если запись в БД не удалась, удаляем сохраненный файл
                if save_path and save_path.exists():
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError as unlink_err:
                        log.error(
                            f"Не удалось удалить файл '{unique_filename}' после ошибки БД: {unlink_err}"
                        )
                raise BadRequestError(
                    "Ошибка при сохранении информации о медиафайле."
                ) from db_exc

        except (MediaValidationError, BadRequestError):
            # Пробрасываем наши ожидаемые ошибки дальше
            # Откат не нужен здесь, так как ошибки произошли до commit или откат был сделан выше
            raise
        except Exception as outer_exc:
            log.exception(
                f"Непредвиденная внешняя ошибка при сохранении медиа {filename}: {outer_exc}"
            )
            await db.rollback()  # Гарантируем откат, если транзакция была начата
            # Попытка удалить файл, если он существует
            if save_path and save_path.exists():
                try:
                    save_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise BadRequestError("Общая ошибка при сохранении медиа.") from outer_exc

    async def delete_media_files(self, file_paths: List[str]) -> None:
        """
        Удаляет список физических медиафайлов с диска асинхронно.

        Логирует ошибки, но не прерывает выполнение из-за ошибки удаления одного файла.

        Args:
            file_paths (List[str]): Список относительных путей к файлам для удаления.
        """
        if not file_paths:
            return

        log.info(f"Запуск удаления {len(file_paths)} физических медиафайлов...")
        delete_tasks = []

        for file_path_str in file_paths:
            full_path = settings.MEDIA_ROOT_PATH / file_path_str.lstrip("/")  # type: ignore[operator]
            # Запускаем синхронное удаление в отдельном потоке
            delete_tasks.append(
                asyncio.to_thread(self._delete_single_file_sync, full_path)
            )

        # Запускаем удаление параллельно
        results = await asyncio.gather(*delete_tasks, return_exceptions=True)

        # Обрабатываем результаты (логируем ошибки)
        success_count = 0

        for i, result in enumerate(results):
            file_to_log = file_paths[i]

            if isinstance(result, Exception):
                # Ошибка будет содержать детали из _delete_single_file_sync
                log.error(f"Ошибка при удалении файла '{file_to_log}': {result}")
            elif result is True:
                success_count += 1
                log.debug(f"Файл '{file_to_log}' успешно удален.")

        log.info(
            f"Завершено удаление файлов: {success_count} успешно из {len(file_paths)}."
        )

    def _delete_single_file_sync(self, file_path: Path) -> bool:
        """
        Синхронно удаляет один файл. Предназначена для запуска через asyncio.to_thread.

        Args:
            file_path (Path): Полный путь к файлу.

        Returns:
            bool: True, если файл успешно удален, False, если файл не найден.

        Raises:
            OSError: При других ошибках удаления файла.
        """
        try:
            os.remove(file_path)  # Используем стандартный os.remove
            log.debug(f"Удаление файла {file_path} успешно.")
            return True
        except FileNotFoundError:
            log.warning(f"Файл для удаления не найден: {file_path}")
            return False
        except OSError as exc:
            log.error(f"Ошибка ОС при удалении файла {file_path}: {exc}")
            # Перевыбрасываем ошибку, чтобы gather ее поймал
            raise

    def get_media_url(self, media: Media) -> str:
        """
        Генерирует URL для доступа к медиафайлу.

        Args:
            media (Media): Объект Media.

        Returns:
            str: Полный URL медиафайла.
        """
        # Убираем / с конца префикса и начала пути файла, если они есть, чтобы избежать двойного //
        url = f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/{media.file_path.lstrip('/')}"
        log.debug(f"Сгенерирован URL для медиа ID {media.id}: {url}")
        return url
