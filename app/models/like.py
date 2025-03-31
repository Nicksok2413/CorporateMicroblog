"""Модель для хранения лайков твитов."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.models.base import Base


class Like(Base):
    """Модель лайка (составной первичный ключ: user_id + tweet_id)."""

    __tablename__ = "likes"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    tweet_id = Column(
        Integer,
        ForeignKey("tweets.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Связи
    user = relationship("User", back_populates="likes")
    tweet = relationship("Tweet", back_populates="likes")
