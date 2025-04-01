"""Модель для хранения лайков твитов."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .tweet import Tweet
    from .user import User


class Like(Base):
    """Модель лайка (составной первичный ключ: user_id + tweet_id)."""
    __tablename__ = "likes"

    # Составной первичный ключ
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id", ondelete="CASCADE"), primary_key=True)

    # Связи (для удобной навигации, если потребуется)
    user: Mapped["User"] = relationship(back_populates="likes")
    tweet: Mapped["Tweet"] = relationship(back_populates="likes")

    # Гарантия уникальности лайка от пользователя для твита
    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="uq_user_tweet_like"),)

    def __repr__(self) -> str:
        return f"<Like(user_id={self.user_id}, tweet_id={self.tweet_id})>"
