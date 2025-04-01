"""Сервис для работы с медиафайлами."""

import os
from pathlib import Path

import aiofiles
import aiofiles.os
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.media import Media
from app.repositories.media import MediaRepository


class MediaService:
    def __init__(self, db: AsyncSession):
        self.repo = MediaRepository(db)
        self.storage_path = Path(settings.STORAGE_PATH)

    async def upload_file(self, user_id: int, file: UploadFile) -> Media:
        """Сохраняет файл и информацию о нем в БД.

        Args:
            user_id: ID пользователя
            file: Файл для сохранения

        Returns:
            Media: Объект медиафайла

        Raises:
            ValueError: При недопустимом типе или размере файла
        """

        # Создаем директорию если не существует
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Генерируем уникальное имя файла
        file_ext = Path(file.filename).suffix
        file_name = f"media_{user_id}_{os.urandom(8).hex()}{file_ext}"
        file_path = self.storage_path / file_name

        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Сохраняем в БД
        media = await self.repo.create_media(
            user_id=user_id,
            filename=file_name
        )

        return media

# v2
# """Сервис для работы с медиафайлами."""

# import uuid
# from pathlib import Path
# from typing import Optional
# import aiofiles
# import aiofiles.os
# from fastapi import UploadFile
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from app.models.media import Media
# from app.schemas.media import MediaResponse
# from app.core.config import settings
# from app.core.exceptions import MediaValidationError
#
#
# class MediaService:
#     def __init__(self, session: AsyncSession):
#         """
#         Инициализация сервиса.
#
#         Args:
#             session: Асинхронная сессия SQLAlchemy
#         """
#         self.session = session
#         self.storage_path = Path(settings.STORAGE_PATH)
#
#     async def upload_file(
#             self,
#             user_id: int,
#             file: UploadFile,
#             content_type: Optional[str] = None
#     ) -> Media:
#         """
#         Асинхронная загрузка файла.
#
#         Args:
#             user_id: ID пользователя
#             file: Файл для загрузки
#             content_type: Опциональный MIME-тип
#
#         Returns:
#             Media: Объект сохраненного медиафайла
#
#         Raises:
#             MediaValidationError: При ошибках загрузки
#         """
#         try:
#             # Генерация уникального имени файла
#             file_ext = Path(file.filename).suffix if file.filename else ""
#             file_name = f"media_{user_id}_{uuid.uuid4().hex}{file_ext}"
#
#             # Создание записи в БД
#             media = Media(
#                 user_id=user_id,
#                 filename=file_name,
#                 content_type=content_type or file.content_type
#             )
#
#             # Обеспечиваем существование директории
#             await self._ensure_storage_dir()
#
#             # Асинхронное сохранение файла
#             await self._save_file_to_disk(file_name, await file.read())
#
#             # Фиксация изменений
#             self.session.add(media)
#             await self.session.commit()
#             await self.session.refresh(media)
#
#             return media
#
#         except Exception as e:
#             await self.session.rollback()
#             await self._cleanup_file(file_name)
#             raise MediaValidationError(f"Ошибка загрузки файла: {str(e)}")
#
#     async def get_media_by_id(self, media_id: int) -> Optional[Media]:
#         """
#         Получение медиафайла по ID.
#
#         Args:
#             media_id: ID медиафайла
#
#         Returns:
#             Optional[Media]: Найденный объект или None
#         """
#         return await self.session.get(Media, media_id)
#
#     async def delete_media(self, media: Media) -> None:
#         """
#         Удаление медиафайла.
#
#         Args:
#             media: Объект медиа для удаления
#
#         Raises:
#             MediaValidationError: При ошибках удаления
#         """
#         try:
#             # Удаление файла
#             if await aiofiles.os.path.exists(media.path):
#                 await aiofiles.os.remove(media.path)
#
#             # Удаление записи из БД
#             await self.session.delete(media)
#             await self.session.commit()
#
#         except Exception as e:
#             await self.session.rollback()
#             raise MediaValidationError(f"Ошибка удаления файла: {str(e)}")
#
#     async def _ensure_storage_dir(self) -> None:
#         """Создает директорию для хранения, если не существует."""
#         try:
#             await aiofiles.os.makedirs(self.storage_path, exist_ok=True)
#         except Exception as e:
#             raise MediaValidationError(f"Ошибка создания директории: {str(e)}")
#
#     async def _save_file_to_disk(self, filename: str, file_data: bytes) -> None:
#         """
#         Асинхронно сохраняет файл на диск.
#
#         Args:
#             filename: Имя файла
#             file_data: Бинарные данные файла
#
#         Raises:
#             MediaValidationError: При ошибках записи
#         """
#         try:
#             async with aiofiles.open(self.storage_path / filename, "wb") as f:
#                 await f.write(file_data)
#         except Exception as e:
#             await self._cleanup_file(filename)
#             raise MediaValidationError(f"Ошибка сохранения файла: {str(e)}")
#
#     async def _cleanup_file(self, filename: str) -> None:
#         """Удаляет файл при ошибках."""
#         if filename:
#             try:
#                 file_path = self.storage_path / filename
#                 if await aiofiles.os.path.exists(file_path):
#                     await aiofiles.os.remove(file_path)
#             except Exception:
#                 pass
#
#     @staticmethod
#     def to_response(media: Media) -> MediaResponse:
#         """
#         Конвертирует модель Media в схему ответа.
#
#         Args:
#             media: Объект медиа
#
#         Returns:
#             MediaResponse: Схема для ответа API
#         """
#         return MediaResponse(
#             id=media.id,
#             url=media.url,
#             content_type=media.content_type
#         )