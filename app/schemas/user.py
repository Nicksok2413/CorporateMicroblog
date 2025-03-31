"""Pydantic-схемы для работы с профилями пользователей."""

from typing import List

from pydantic import BaseModel

from app.schemas.follow import UserFollowStats


class UserProfileResponse(BaseModel):
    """Схема ответа с профилем пользователя.

    Fields:
        id: ID пользователя
        name: Имя пользователя
        followers_count: Количество подписчиков
        following_count: Количество подписок
        is_following: Подписан ли текущий пользователь
    """
    id: int
    name: str
    followers_count: int
    following_count: int
    is_following: bool


class UserDetailResponse(UserProfileResponse):
    """Расширенная схема профиля с деталями подписок.

    Fields:
        followers: Список подписчиков
        following: Список подписок
    """
    followers: List[UserFollowStats]
    following: List[UserFollowStats]
