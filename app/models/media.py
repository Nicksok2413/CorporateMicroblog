"""Модель для хранения информации о медиафайлах."""

from pathlib import Path
from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
# Импорт нужен, если используем переменную, а не строку в relationship(secondary=...)
from .tweet import tweet_media_association_table

if TYPE_CHECKING:
    from .tweet import Tweet


class Media(Base):
    """Модель медиафайла с метаданными и связями.

    Attributes:
        id: Уникальный идентификатор
        file_path: Имя файла в хранилище
    """
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Путь к файлу относительно корня статики (или как вы решите)
    # unique=True, если предполагается, что каждый файл уникален (например, по UUID имени)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    # Связь с твитами
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
        return f"<Media(id={self.id}, path='{self.file_path}')>"
