"""Модель SQLAlchemy для Like (Лайк)."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from .tweet import Tweet
    from .user import User


class Like(Base):
    """
    Представляет действие 'лайк' от пользователя (User) на твит (Tweet).

    Выступает в роли ассоциативного объекта между User и Tweet для лайков.

    Attributes:
        user_id: Внешний ключ, ссылающийся на пользователя (User), поставившего лайк
        tweet_id: Внешний ключ, ссылающийся на твит (Tweet), который был лайкнут
        user: Связь с объектом лайкнувшего пользователя (User)
        tweet: Связь с объектом лайкнутого твита (Tweet)
    """
    __tablename__ = "likes"

    # Составной первичный ключ гарантирует, что пользователь может лайкнуть твит только один раз.
    # CASCADE гарантирует, что лайки удаляются, если пользователь или твит удалены.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"), primary_key=True
    )

    # Связи (опциональны, но могут быть полезны для навигации)
    user: Mapped["User"] = relationship(back_populates="likes")
    tweet: Mapped["Tweet"] = relationship(back_populates="likes")

    # Явное ограничение уникальности (покрывается составным первичным ключом, но хорошо для ясности)
    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="uq_user_tweet_like"),)
