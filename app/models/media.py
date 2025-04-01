"""Модель SQLAlchemy для Media (Медиафайл)."""

from pathlib import Path
from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from .associations import tweet_media_association_table
from .base import Base

if TYPE_CHECKING:
    from .tweet import Tweet


class Media(Base):
    """
    Представляет медиафайл (например, изображение), который может быть прикреплен к твитам.

    Attributes:
        id: Первичный ключ, идентификатор медиафайла
        file_path: Путь к медиафайлу (относительно корневой папки медиа)
        tweets: Список твитов, к которым прикреплен этот медиафайл
    """
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Путь относительно настроенного корневого каталога для хранения медиа.
    # unique=True предполагает, что генерируемые имена файлов (например, UUID) предотвращают коллизии.
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    # Связи
    tweets: Mapped[List["Tweet"]] = relationship(
        secondary=tweet_media_association_table, back_populates="attachments"
    )

    @property
    def url(self) -> str:
        """Генерирует URL для доступа к файлу.

        Returns:
            str: Относительный URL вида /media/files/{filename}
        """
        return f"/media/files/{self.file_path}"

    @property
    def path(self) -> Path:
        """Абсолютный путь к файлу в хранилище.

        Returns:
            Path: Полный путь к файлу
        """
        return Path(settings.STORAGE_PATH) / self.file_path


    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта Media.

        Returns:
            Строковое представление медиафайла.
        """
        return f"<Media(id={self.id}, path='{self.file_path}')>"
