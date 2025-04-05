"""Модель SQLAlchemy для Tweet (Твит)."""

from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, tweet_media_association_table

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
        author_id: Внешний ключ, ссылающийся на автора (User)
        author: Связь с объектом User, автором твита
        likes: Список лайков, полученных этим твитом
        attachments: Список объектов Media, прикрепленных к этому твиту
    """
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(String(280), nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Связи
    author: Mapped["User"] = relationship(back_populates="tweets")
    likes: Mapped[List["Like"]] = relationship(
        back_populates="tweet", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Media"]] = relationship(
        secondary=tweet_media_association_table, back_populates="tweets"
    )
