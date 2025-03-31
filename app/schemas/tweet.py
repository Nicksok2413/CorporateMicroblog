"""Pydantic-схемы для твитов."""

from typing import List, Optional

from pydantic import BaseModel, Field


class TweetCreate(BaseModel):
    """Схема для создания твита.

    Fields:
        tweet_data: Текст твита (макс. 280 символов)
        tweet_media_ids: Список ID медиавложений
    """
    tweet_data: str = Field(..., max_length=280)
    tweet_media_ids: Optional[List[int]] = None


class TweetResponse(BaseModel):
    """Схема ответа с твитом.

    Fields:
        id: ID твита
        content: Текст
        author_id: ID автора
        likes_count: Количество лайков
        attachments: Ссылки на медиа
    """
    id: int
    content: str
    author_id: int
    likes_count: int
    attachments: List[str]
