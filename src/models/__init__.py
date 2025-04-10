"""
Пакет моделей SQLAlchemy.

Экспортирует базовый класс Base, все определенные модели и ассоциативные таблицы,
чтобы Alembic мог обнаружить их для автогенерации миграций.
"""
from .associations import tweet_media_association_table
from .base import Base
from .follow import Follow
from .like import Like
from .media import Media
from .tweet import Tweet
from .user import User
