"""Модель твита для БД."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tweet(Base):
    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(280), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"))

    # Связи
    author = relationship("User", back_populates="tweets")
    likes = relationship("Like", back_populates="tweet", cascade="all, delete-orphan")
    media_links = relationship("TweetMedia", back_populates="tweet", cascade="all, delete-orphan")
