"""Модель пользователя для микросервиса блогов."""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """Модель пользователя с дополнительными атрибутами.

    Attributes:
        id: Уникальный идентификатор
        name: Имя пользователя
        api_key: Уникальный ключ для аутентификации
        is_demo: Флаг демо-пользователя
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)

    # Связи
    tweets = relationship("Tweet", back_populates="author", cascade="all, delete")
    likes = relationship("Like", back_populates="user", cascade="all, delete")
    followers = relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        back_populates="followed",
        cascade="all, delete"
    )
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete"
    )
    media = relationship("Media", back_populates="user", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name})>"
