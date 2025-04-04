"""
Пакет сервисов приложения.

Содержит бизнес-логику, координирует работу репозиториев
и подготавливает данные для API роутов.

Экспортирует экземпляры сервисов для использования в API и других сервисах.
"""
from .follow_service import FollowService
from .media_service import MediaService
from .tweet_service import TweetService
from .user_service import UserService

# __all__ = [
#     "user_service",
#     "media_service",
#     "tweet_service",
#     "follow_service",
# ]
