"""Pydantic-схемы для твитов."""

from typing import List, Optional

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.media import MediaResponse
from app.schemas.user import UserResponse


class TweetCreate(BaseSchema):
    """Схема для создания твита.

    Fields:
        tweet_data: Текст твита (макс. 280 символов)
        tweet_media_ids: Список ID медиавложений
    """
    tweet_data: str = Field(..., max_length=280)
    tweet_media_ids: Optional[List[int]] = Field(None, description="ID прикрепленных медиафайлов")


class TweetResponse(BaseSchema):
    """Схема ответа с твитом.

    Fields:
        id: ID твита
        content: Текст
        author: Автор
        is_liked: Есть ли лайки
        likes_count: Количество лайков
        attachments: Ссылки на медиа
    """
    id: int
    content: str
    author: UserResponse
    is_liked: bool
    likes_count: int
    attachments: List[MediaResponse]
