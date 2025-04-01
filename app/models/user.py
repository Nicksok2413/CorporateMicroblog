"""Модель SQLAlchemy для User (Пользователь)."""

from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .follow import Follow
    from .like import Like
    from .tweet import Tweet


class User(Base):
    """
    Представляет пользователя в приложении.

    Attributes:
        id: Первичный ключ, идентификатор пользователя
        name: Имя пользователя
        api_key: Уникальный API ключ для аутентификации пользователя
        tweets: Список твитов, написанных пользователем
        likes: Список лайков, поставленных пользователем
        following: Список связей подписки, где этот пользователь является подписчиком
        followers: Список связей подписки, где этот пользователь является тем, на кого подписаны
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    # Связи
    tweets: Mapped[List["Tweet"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    likes: Mapped[List["Like"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    # Пользователи, на которых подписан данный пользователь
    following: Mapped[List["Follow"]] = relationship(
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    # Пользователи, подписанные на данного пользователя
    followers: Mapped[List["Follow"]] = relationship(
        foreign_keys="Follow.following_id",
        back_populates="followed_user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта User.

        Returns:
            Строковое представление пользователя.
        """
        return f"<User(id={self.id}, name='{self.name}')>"