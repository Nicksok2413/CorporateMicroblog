"""
Пакет схем Pydantic.

Определяет структуры данных для валидации запросов API,
сериализации ответов и передачи данных между слоями приложения.

Экспортирует основные схемы для использования в других модулях.
"""

from .base import ResultFalseWithError, ResultTrue, TunedModel
from .media import MediaCreate, MediaCreateResult
from .tweet import (
    LikeInfo,
    TweetActionResult,
    TweetAuthor,
    TweetCreateRequest,
    TweetCreateResult,
    TweetFeedResult,
    TweetInFeed,
)
from .user import BaseUser, UserProfile, UserProfileResult

# __all__ = [
#     # Base
#     "ResultTrue",
#     "ResultFalseWithError",
#     "TunedModel",
#     # Media
#     "MediaCreate",
#     "MediaCreateResult",
#     "MediaOut",
#     # Tweet
#     "TweetCreateRequest",
#     "TweetCreateResult",
#     "TweetActionResult",
#     "TweetInFeed",
#     "TweetFeedResult",
#     "TweetAuthor",
#     "LikeInfo",
#     # User
#     "BaseUser",
#     "UserProfile",
#     "UserProfileResult",
# ]
