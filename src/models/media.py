"""Модель SQLAlchemy для Media (Медиафайл)."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base

if TYPE_CHECKING:  # pragma: no cover
    from .tweet import Tweet


class Media(Base):
    """
    Представляет медиафайл (например, изображение), который может быть прикреплен к твиту.

    Attributes:
        id: Первичный ключ, идентификатор медиафайла
        file_path: Путь к медиафайлу (относительно корневой папки медиа)
        tweet_id: Внешний ключ на твит, к которому прикреплен файл
        tweet: Связь с объектом Tweet
    """
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Путь относительно настроенного корневого каталога для хранения медиа.
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    # Внешний ключ на твит
    tweet_id: Mapped[int | None] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"),  # Удаление твита удалит медиа
        nullable=True,  # Медиа может существовать без твита (сразу после загрузки)
        index=True  # Индекс по tweet_id для быстрого поиска медиа для твита
    )

    # Связи
    # Многие-к-одному с твитом
    tweet: Mapped["Tweet"] = relationship(back_populates="attachments")
