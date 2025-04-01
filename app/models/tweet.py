"""Модель твита для БД."""

import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .like import Like
    from .media import Media
    from .user import User

# --- Ассоциативная таблица для связи Tweet <-> Media ---
# Ее можно вынести в отдельный файл models/associations.py или оставить здесь
tweet_media_association_table = Table(
    "tweet_media_association",
    Base.metadata,
    Column("tweet_id", Integer, ForeignKey("tweets.id", ondelete="CASCADE"), primary_key=True),
    Column("media_id", Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    # ondelete="CASCADE" означает, что при удалении твита или медиа, связь в этой таблице будет удалена
)


# --- Конец ассоциативной таблицы ---

class Tweet(Base):
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True  # Индекс по дате для сортировки ленты
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                           index=True)  # ondelete=CASCADE, если твиты удаляются при удалении юзера

    # Связи
    author: Mapped["User"] = relationship(back_populates="tweets")
    likes: Mapped[List["Like"]] = relationship(
        back_populates="tweet", cascade="all, delete-orphan"  # При удалении твита удалять его лайки
    )
    attachments: Mapped[List["Media"]] = relationship(
        secondary=tweet_media_association_table, back_populates="tweets"
        # cascade для M2M обычно не нужен здесь, т.к. удаление связи происходит через CASCADE в FK ассоциативной таблицы
    )

    def __repr__(self) -> str:
        return f"<Tweet(id={self.id}, author_id={self.author_id}, content='{self.content[:20]}...')>"
