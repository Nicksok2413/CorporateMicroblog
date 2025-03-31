"""Pydantic-схемы для работы с подписками."""

from typing import List

from app.schemas.base import BaseSchema


class FollowStats(BaseSchema):
    """Схема статистики подписки.

    Fields:
        id: ID пользователя
        name: Имя пользователя
    """
    id: int
    name: str


class FollowResponse(BaseSchema):
    """Схема ответа для операций с подписками.

    Fields:
        user_id: ID целевого пользователя
        followers_count: Количество подписчиков
        following_count: Количество подписок
        is_following: Подписан ли текущий пользователь
    """
    user_id: int
    followers_count: int
    following_count: int
    is_following: bool


class UserFollowStats(BaseSchema):
    """Детализированная статистика подписок.

    Fields:
        followers: Список подписчиков
        following: Список подписок
    """
    followers: List[FollowStats]
    following: List[FollowStats]
