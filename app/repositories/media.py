"""Репозиторий для работы с моделью Media."""

from app.models.media import Media
from app.repositories.base import BaseRepository
from app.schemas.media import MediaCreate


class MediaRepository(BaseRepository[Media, MediaCreate]):
    """
    Репозиторий для выполнения CRUD операций с моделью Media.
    """
    # В данном случае базовых CRUD достаточно
    pass
