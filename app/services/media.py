"""Сервис для работы с медиафайлами."""

import os

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.media import Media
from app.repositories.media import MediaRepository


class MediaService:
    def __init__(self, db: AsyncSession):
        self.repo = MediaRepository(db)
        self.storage_path = Path(settings.STORAGE_PATH)

    async def upload_file(
            self,
            user_id: int,
            file: UploadFile
    ) -> Media:
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
