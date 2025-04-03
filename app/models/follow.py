"""Модель SQLAlchemy для Follow (Подписка)."""

from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .user import User


class Follow(Base):
    """
    Представляет отношение 'подписка' между двумя пользователями (Users).

    Выступает в роли ассоциативного объекта, указывающего, что один пользователь (follower)
    подписан на другого (followed_user).

    Attributes:
        follower_id: Внешний ключ, ссылающийся на подписавшегося пользователя (User)
        following_id: Внешний ключ, ссылающийся на пользователя, на которого подписываются (User)
        follower: Связь с объектом пользователя-подписчика (User)
        followed_user: Связь с объектом пользователя, на которого подписались (User)
    """
    __tablename__ = "follows"

    # Составной первичный ключ гарантирует, что пользователь подписывается на другого только один раз.
    # CASCADE гарантирует, что записи о подписках удаляются, если любой из пользователей удален.
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # Связи с явным указанием foreign_keys из-за двух FK на одну и ту же таблицу (users)
    follower: Mapped["User"] = relationship(
        "User", foreign_keys=[follower_id], back_populates="following"
    )
    followed_user: Mapped["User"] = relationship(
        "User", foreign_keys=[following_id], back_populates="followers"
    )

    __table_args__ = (
        # Гарантия уникальности пары подписчик-подписываемый.
        UniqueConstraint("follower_id", "following_id", name="uq_follower_following"),
        # Запрет пользователям подписываться на самих себя.
        CheckConstraint("follower_id != following_id", name="ck_follow_no_self_follow"),
    )
