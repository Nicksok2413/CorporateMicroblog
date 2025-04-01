"""Модель SQLAlchemy для Tweet (Твит)."""

import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import tweet_media_association_table
from .base import Base

if TYPE_CHECKING:
    from .like import Like
    from .media import Media
    from .user import User


class Tweet(Base):
    """
    Представляет твит, опубликованный пользователем.

    Attributes:
        id: Первичный ключ, идентификатор твита
        content: Текстовое содержимое твита (макс. 280 символов)
        created_at: Временная метка создания твита
        author_id: Внешний ключ, ссылающийся на автора (User)
        author: Связь с объектом User, автором твита
        likes: Список лайков, полученных этим твитом
        attachments: Список объектов Media, прикрепленных к этому твиту
    """
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    # onDelete=CASCADE: если автор (User) удаляется, его твиты также удаляются.
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Связи
    author: Mapped["User"] = relationship(back_populates="tweets")
    # onDelete=CASCADE обрабатывается через ForeignKey в модели Like
    likes: Mapped[List["Like"]] = relationship(
        back_populates="tweet", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Media"]] = relationship(
        secondary=tweet_media_association_table, back_populates="tweets"
    )

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта Tweet.

        Returns:
            Строковое представление твита.
        """
        return f"<Tweet(id={self.id}, author_id={self.author_id}, content='{self.content[:20]}...')>"
