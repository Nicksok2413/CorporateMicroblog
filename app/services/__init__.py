"""
Пакет сервисов приложения.

Содержит бизнес-логику, координирует работу репозиториев
и подготавливает данные для API роутов.

Экспортирует экземпляры сервисов для использования в API и других сервисах.
"""
from .user_service import user_service
from .media_service import media_service
from .tweet_service import tweet_service
from .follow_service import follow_service

__all__ = [
    "user_service",
    "media_service",
    "tweet_service",
    "follow_service",
]
