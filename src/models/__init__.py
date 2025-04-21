"""
Пакет моделей SQLAlchemy.

Экспортирует базовый класс Base, все определенные модели и ассоциативные таблицы,
чтобы Alembic мог обнаружить их для автогенерации миграций.
"""

from .base import Base
from .follow import Follow
from .like import Like
from .media import Media
from .tweet import Tweet
from .user import User

# Экспортируем модели и базовый класс
__all__ = [
    "Base",
    "Follow",
    "Like",
    "Media",
    "Tweet",
    "User",
]
