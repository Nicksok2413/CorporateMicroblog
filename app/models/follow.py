"""Модель для хранения подписок пользователей."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Follow(Base):
    """Модель подписки."""
    __tablename__ = "follows"

    # Кто подписывается
    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # На кого подписывается
    following_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Связи с явным указанием foreign_keys
    follower: Mapped["User"] = relationship(
        "User", foreign_keys=[follower_id], back_populates="following"
    )
    followed_user: Mapped["User"] = relationship(
        "User", foreign_keys=[following_id], back_populates="followers"
    )  # Используем "User", чтобы не импортировать явно

    __table_args__ = (
        # Уникальность пары подписчик-подписываемый
        UniqueConstraint("follower_id", "following_id", name="uq_follower_following"),
        # Запрет подписки на самого себя
        CheckConstraint("follower_id != following_id", name="ck_follow_no_self_follow"),
    )

    def __repr__(self) -> str:
        return f"<Follow(follower={self.follower_id}, following={self.following_id})>"
