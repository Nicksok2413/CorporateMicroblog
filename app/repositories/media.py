"""Репозиторий для работы с моделью Media."""

from typing import Optional  # Добавим Optional для схемы Update, если она появится

from app.models.media import Media
from app.repositories.base import BaseRepository
from app.schemas.media import MediaCreate  # Импортируем реальную схему


class MediaRepository(BaseRepository[Media, MediaCreate, None]):  # Указываем схему Create, Update = None
    """
    Репозиторий для выполнения CRUD операций с моделью Media.
    """
    # В данном случае специфичных методов может и не быть,
    # базовых CRUD достаточно.
    pass


# Создаем экземпляр репозитория
media_repo = MediaRepository(Media)
