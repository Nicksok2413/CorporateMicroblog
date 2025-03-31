"""Pydantic-схемы для работы с лайками."""

from pydantic import BaseModel


class LikeResponse(BaseModel):
    """Схема ответа при работе с лайками.

    Fields:
        tweet_id: ID твита
        likes_count: Количество лайков
        is_liked: Поставил ли текущий пользователь лайк
    """
    tweet_id: int
    likes_count: int
    is_liked: bool
