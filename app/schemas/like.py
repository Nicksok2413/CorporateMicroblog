"""Pydantic-схемы для работы с лайками."""

from app.schemas.base import BaseSchema


class LikeResponse(BaseSchema):
    """Схема ответа при работе с лайками.

    Fields:
        tweet_id: ID твита
        is_liked: Поставил ли текущий пользователь лайк
        likes_count: Количество лайков
    """
    tweet_id: int
    is_liked: bool
    likes_count: int
