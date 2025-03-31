"""Pydantic-схемы для работы с профилями пользователей."""

from typing import List

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.follow import UserFollowStats


class UserBase(BaseSchema):
    """Базовая схема пользователя.

    Fields:
        name: Имя пользователя
    """
    name: str = Field(..., max_length=50)


class UserCreate(UserBase):
    """Схема для создания пользователя.

    Fields:
        name: Имя пользователя
        api_key: API-ключ
    """
    api_key: str = Field(..., max_length=64)


class UserResponse(UserBase):
    """Схема ответа с данными пользователя.

    Fields:
        id: ID пользователя
        name: Имя пользователя
        is_demo: Является ли демо-пользователем или нет
    """
    id: int
    is_demo: bool


class UserProfileResponse(UserResponse):
    """Схема ответа с профилем пользователя.

    Fields:
        id: ID пользователя
        name: Имя пользователя
        followers_count: Количество подписчиков
        following_count: Количество подписок
        is_following: Подписан ли текущий пользователь
    """
    followers_count: int
    following_count: int
    is_following: bool


class UserDetailResponse(UserProfileResponse):
    """Расширенная схема профиля с деталями подписок.

    Fields:
        id: ID пользователя
        name: Имя пользователя
        followers_count: Количество подписчиков
        following_count: Количество подписок
        is_following: Подписан ли текущий пользователь
        followers: Список подписчиков
        following: Список подписок
    """
    followers: List[UserFollowStats]
    following: List[UserFollowStats]
