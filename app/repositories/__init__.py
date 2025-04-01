"""
Пакет репозиториев для взаимодействия с базой данных.

Предоставляет абстракцию над источником данных (SQLAlchemy ORM)
и инкапсулирует логику запросов к БД.

Экспортирует экземпляры репозиториев для использования в слое сервисов.
"""
from .user import user_repo
from .tweet import tweet_repo
from .media import media_repo
from .like import like_repo
from .follow import follow_repo

__all__ = [
    "user_repo",
    "tweet_repo",
    "media_repo",
    "like_repo",
    "follow_repo",
]