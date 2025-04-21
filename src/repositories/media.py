"""Репозиторий для работы с моделью Media."""

from src.models.media import Media
from src.repositories.base import BaseRepository
from src.schemas.media import MediaCreate


class MediaRepository(BaseRepository[Media, MediaCreate]):
    """
    Репозиторий для выполнения CRUD операций с моделью Media.
    В нашем случае базовых CRUD достаточно.
    """

    pass
