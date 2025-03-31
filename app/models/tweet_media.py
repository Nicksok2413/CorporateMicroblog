"""Связь твитов и медиа."""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class TweetMedia(Base):
    """Связующая модель для медиа в твитах (many-to-many)."""

    __tablename__ = "tweet_media"

    tweet_id = Column(
        Integer,
        ForeignKey("tweets.id", ondelete="CASCADE"),
        primary_key=True
    )
    media_id = Column(
        Integer,
        ForeignKey("media.id", ondelete="CASCADE"),
        primary_key=True
    )
    position = Column(Integer, default=0)  # Порядок отображения

    # Связи
    tweet = relationship("Tweet", back_populates="media_links")
    media = relationship("Media", back_populates="tweet_media")
