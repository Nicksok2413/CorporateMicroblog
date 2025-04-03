"""Ассоциативные таблицы SQLAlchemy для связей многие-ко-многим."""

from sqlalchemy import Column, ForeignKey, Integer, Table

from app.models.base import Base

# Ассоциативная таблица для связи many-to-many между Tweets и Media
tweet_media_association_table = Table(
    "tweet_media_association",
    Base.metadata,
    # Внешний ключ к таблице твитов. Удаление твита удалит связь.
    Column(
        "tweet_id",
        Integer,
        ForeignKey("tweets.id", ondelete="CASCADE"),
        primary_key=True
    ),
    # Внешний ключ к таблице медиа. Удаление медиа удалит связь.
    Column(
        "media_id",
        Integer,
        ForeignKey("media.id", ondelete="CASCADE"),
        primary_key=True
    ),
)
