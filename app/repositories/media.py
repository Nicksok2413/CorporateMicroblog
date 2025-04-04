"""Репозиторий для работы с моделью Media."""

from app.models.media import Media
from app.repositories.base import BaseRepository
from app.schemas.media import MediaCreate


class MediaRepository(BaseRepository[Media, MediaCreate, None]):
    """
    Репозиторий для выполнения CRUD операций с моделью Media.
    """
    # В данном случае базовых CRUD достаточно
    pass


# Создаем экземпляр репозитория
media_repo = MediaRepository(Media)
