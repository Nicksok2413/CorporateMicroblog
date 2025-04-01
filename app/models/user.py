from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .follow import Follow
    from .like import Like
    from .tweet import Tweet


class User(Base):
    """Модель пользователя с дополнительными атрибутами.

    Attributes:
        id: Уникальный идентификатор
        name: Имя пользователя
        api_key: Уникальный ключ для аутентификации
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Связи
    tweets: Mapped[List["Tweet"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"  # При удалении юзера удалять его твиты
    )
    likes: Mapped[List["Like"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"  # При удалении юзера удалять его лайки
    )
    following: Mapped[List["Follow"]] = relationship(
        foreign_keys="Follow.follower_id", back_populates="follower", cascade="all, delete-orphan"
    )
    followers: Mapped[List["Follow"]] = relationship(
        foreign_keys="Follow.following_id", back_populates="followed_user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}')>"
