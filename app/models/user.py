from sqlalchemy import Boolean, Integer, Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.follow import Follow


class User(Base):
    """Модель пользователя для корпоративной системы."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)

    # Связи
    tweets = relationship("Tweet", back_populates="author")
    likes = relationship("Like", back_populates="user")
    followers = relationship("Follow", foreign_keys=[Follow.followed_id], back_populates="followed")
    following = relationship("Follow", foreign_keys=[Follow.follower_id], back_populates="follower")
