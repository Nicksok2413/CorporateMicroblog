"""Репозиторий для работы с моделью Media."""

# Импорты для схем здесь не обязательны, но могут понадобиться для type hinting
# в специфичных методах, если такие будут
from typing import TYPE_CHECKING

from app.models.media import Media
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    # Импортируем схемы для аннотаций, если нужно
    from app.schemas.media import MediaCreate


class MediaRepository(BaseRepository[Media, "MediaCreate", None]):  # Указываем схемы
    """
    Репозиторий для выполнения CRUD операций с моделью Media.
    """
    # В данном случае специфичных методов может и не быть,
    # базовых CRUD достаточно.
    pass


# Создаем экземпляр репозитория
media_repo = MediaRepository(Media)
