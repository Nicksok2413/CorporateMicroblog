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
    TweetAuthor,  # Экспортируем, если используется где-то еще
    LikeInfo,  # Экспортируем, если используется где-то еще
)
from .user import BaseUser, UserProfile, UserProfileResult

# Если создавали схемы для Like и Follow, их тоже нужно экспортировать
# from .like import LikeCreate, LikeOut
# from .follow import FollowCreate

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
    # Like (если есть)
    # "LikeCreate",
    # "LikeOut",
    # Follow (если есть)
    # "FollowCreate",
]
