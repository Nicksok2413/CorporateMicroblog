"""
Пакет схем Pydantic.

Определяет структуры данных для валидации запросов API,
сериализации ответов и передачи данных между слоями приложения.

Экспортирует основные схемы для использования в других модулях.
"""

from .base import ResultTrue, ResultFalseWithError, TunedModel
from .media import MediaCreate, MediaCreateResult, MediaOut
from .tweet import (
    TweetCreateRequest,
    TweetCreateResult,
    TweetActionResult,
    TweetInFeed,
    TweetFeedResult,
    TweetAuthor,
    LikeInfo,
)
from .user import BaseUser, UserProfile, UserProfileResult

__all__ = [
    # Base
    "ResultTrue",
    "ResultFalseWithError",
    "TunedModel",
    # Media
    "MediaCreate",
    "MediaCreateResult",
    "MediaOut",
    # Tweet
    "TweetCreateRequest",
    "TweetCreateResult",
    "TweetActionResult",
    "TweetInFeed",
    "TweetFeedResult",
    "TweetAuthor",
    "LikeInfo",
    # User
    "BaseUser",
    "UserProfile",
    "UserProfileResult",
]
