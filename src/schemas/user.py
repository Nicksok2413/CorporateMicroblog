"""Схемы Pydantic для модели User."""

from typing import List

from pydantic import Field

from src.schemas.base import ResultTrue, TunedModel


# --- Базовые блоки ---
class BaseUser(TunedModel):
    """
    Базовая схема пользователя, содержащая только ID и имя.

    Используется для вложенного представления в других схемах (автор, лайки, подписчики).

    Fields:
        id (int): Уникальный идентификатор пользователя
        name (str): Имя пользователя
    """
    id: int
    name: str


# --- Схемы для API ответов ---
# noinspection PyDataclass
class UserProfile(TunedModel):
    """
    Схема для профиля пользователя.

    Включает информацию о подписчиках и подписках.

    Fields:
        id (int): Уникальный идентификатор пользователя
        name (str): Имя пользователя
        followers (List[BaseUser]): Список пользователей, подписанных на этого пользователя
        following (List[BaseUser]): Список пользователей, на которых подписан этот пользователь
    """
    id: int
    name: str
    followers: List[BaseUser] = Field(default_factory=list)
    following: List[BaseUser] = Field(default_factory=list)


class UserProfileResult(ResultTrue):
    """
    Схема ответа для эндпоинтов получения профиля пользователя.

    Fields:
        result (bool): Всегда True
        user (UserProfile): Данные профиля пользователя
    """
    user: UserProfile
