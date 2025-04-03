"""Схемы Pydantic для модели Tweet."""

from typing import List, Optional

from pydantic import Field

from app.schemas.base import ResultTrue, TunedModel, BaseModel
from app.schemas.user import BaseUser


# --- Входные данные API ---
class TweetCreateRequest(BaseModel):
    """
    Схема запроса на создание нового твита.

    Fields:
        tweet_data (str): Текст твита.
        tweet_media_ids (Optional[List[int]]): Список ID медиафайлов для прикрепления.
    """
    tweet_data: str = Field(..., min_length=1, max_length=280, description="Текст твита (1-280 символов)")
    tweet_media_ids: Optional[List[int]] = Field(None, description="Список ID медиафайлов для прикрепления")


# --- Внутренние схемы (для передачи между слоями) ---
class TweetCreateInternal(BaseModel):
    """
    Внутренняя схема для создания объекта Tweet в репозитории.

    Содержит только поля, напрямую соответствующие модели Tweet.

    Fields:
        content (str): Текст твита.
        author_id (int): ID автора твита.
    """
    content: str
    author_id: int


# --- Выходные данные API ---

class TweetCreateResult(ResultTrue):
    """
    Схема ответа при успешном создании твита.

    Fields:
        result (bool): Всегда True.
        tweet_id (int): ID созданного твита.
    """
    tweet_id: int


class TweetActionResult(ResultTrue):
    """
    Общая схема успешного ответа для действий с твитом (удаление, лайк/анлайк).

    Fields:
        result (bool): Всегда True.
    """
    pass


class LikeInfo(BaseUser):
    """
    Информация о пользователе, поставившем лайк.
    Наследует id и name от BaseUser.

    Fields:
        id (int): ID пользователя.
        name (str): Имя пользователя.
    """
    pass


class TweetAuthor(BaseUser):
    """
    Информация об авторе твита.
    Наследует id и name от BaseUser.

    Fields:
        id (int): ID автора.
        name (str): Имя автора.
    """
    pass


# noinspection PyDataclass
class TweetInFeed(TunedModel):
    """
    Схема представления одного твита в ленте.

    Fields:
        id (int): ID твита.
        content (str): Текст твита.
        attachments (List[str]): Список URL прикрепленных медиафайлов.
        author (TweetAuthor): Информация об авторе твита.
        likes (List[LikeInfo]): Список пользователей, лайкнувших твит.
        created_at (datetime.datetime): Дата и время создания твита (добавлено для информации).
    """
    id: int
    content: str
    attachments: List[str] = Field(default_factory=list)
    author: TweetAuthor
    likes: List[LikeInfo] = Field(default_factory=list)


# noinspection PyDataclass
class TweetFeedResult(ResultTrue):
    """
    Схема ответа для эндпоинта получения ленты твитов.

    Fields:
        result (bool): Всегда True.
        tweets (List[TweetInFeed]): Список твитов в ленте.
    """
    tweets: List[TweetInFeed] = Field(default_factory=list)
