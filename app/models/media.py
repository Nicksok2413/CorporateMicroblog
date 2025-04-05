"""Модель SQLAlchemy для Media (Медиафайл)."""

from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, tweet_media_association_table

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
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    # Связи
    tweets: Mapped[List["Tweet"]] = relationship(
        secondary=tweet_media_association_table, back_populates="attachments"
    )
