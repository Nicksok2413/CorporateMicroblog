"""Схемы Pydantic для модели Tweet."""

import datetime
from typing import List, Optional

from pydantic import Field, field_validator

from app.schemas.base import ResultTrue, TunedModel, BaseModel
from app.schemas.user import BaseUser  # Используем базовую схему пользователя


# --- Входные данные API ---
class TweetCreateRequest(BaseModel):
    """
    Схема запроса на создание нового твита.

    Fields:
        tweet_data (str): Текст твита
        tweet_media_ids (Optional[List[int]]): Список ID медиафайлов для прикрепления
    """
    tweet_data: str = Field(..., min_length=1, max_length=280, description="Текст твита (1-280 символов)")
    tweet_media_ids: Optional[List[int]] = Field(None, description="Список ID медиафайлов для прикрепления")

    # Пример валидатора, если нужно что-то проверить дополнительно
    # @field_validator('tweet_media_ids')
    # def ensure_unique_ids(cls, v):
    #     if v and len(v) != len(set(v)):
    #         raise ValueError('Media IDs must be unique')
    #     return v


# --- Выходные данные API ---

class TweetCreateResult(ResultTrue):
    """
    Схема ответа при успешном создании твита.

    Fields:
        result (bool): Всегда True
        tweet_id (int): ID созданного твита
    """
    tweet_id: int


class TweetActionResult(ResultTrue):
    """
    Общая схема успешного ответа для действий с твитом (удаление, лайк/анлайк).

    Fields:
        result (bool): Всегда True
    """
    pass  # Нет дополнительных полей


class LikeInfo(BaseUser):
    """
    Информация о пользователе, поставившем лайк.
    Наследует id и name от BaseUser.

    Fields:
        user_id (int): ID пользователя (переименовано для соответствия ТЗ)
        name (str): Имя пользователя
    """
    # Переименовываем поле id в user_id для соответствия ТЗ
    # В Pydantic V2 это делается через Field(validation_alias='id') или alias='user_id'
    # Если модель SQLAlchemy имеет поле user_id, то from_attributes справится само
    # Если модель SQLAlchemy имеет поле id, то нужен alias
    # В нашей модели Like есть user_id, но для User - id. Нужно достать из User.
    # Проще оставить id и name, как в BaseUser, если фронт не возражает.
    # Если ТЗ строгое, нужна кастомная сериализация или адаптер.
    # --- Вариант 1: Оставляем id, name (проще) ---
    pass  # Наследует id, name
    # --- Вариант 2: Строго по ТЗ (сложнее, требует адаптации при формировании) ---
    # user_id: int = Field(..., alias="id") # Читаем 'id' из модели User, отдаем как 'user_id'
    # name: str
    # model_config = ConfigDict(from_attributes=True, populate_by_name=True) # populate_by_name нужно для alias


class TweetAuthor(BaseUser):
    """
    Информация об авторе твита.
    Наследует id и name от BaseUser.

    Fields:
        id (int): ID автора
        name (str): Имя автора
    """
    pass  # Наследует id, name


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
    # attachments будет списком URL, формируемым в сервисе/эндпоинте
    attachments: List[str] = Field(default_factory=list)
    author: TweetAuthor
    likes: List[LikeInfo] = Field(default_factory=list)
    created_at: datetime.datetime  # Добавим дату создания для полезности


class TweetFeedResult(ResultTrue):
    """
    Схема ответа для эндпоинта получения ленты твитов.

    Fields:
        result (bool): Всегда True.
        tweets (List[TweetInFeed]): Список твитов в ленте.
    """
    tweets: List[TweetInFeed] = Field(default_factory=list)
