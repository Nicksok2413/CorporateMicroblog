"""
Пакет репозиториев для взаимодействия с базой данных.

Предоставляет абстракцию над источником данных (SQLAlchemy ORM)
и инкапсулирует логику запросов к БД.

Экспортирует экземпляры репозиториев для использования в слое сервисов.
"""
from .follow import FollowRepository
from .like import LikeRepository
from .media import MediaRepository
from .tweet import TweetRepository
from .user import UserRepository
