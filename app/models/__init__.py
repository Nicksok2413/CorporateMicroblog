# Этот файл нужен, чтобы Alembic легко находил все модели.
# Импортируйте Base и все ваши модели.
from .base import Base
from .follow import Follow
from .like import Like
from .media import Media
from .tweet import Tweet, tweet_media_association_table  # Импортируем и таблицу
from .user import User

# Можно определить __all__, если хотите явно указать экспортируемые имена
# __all__ = ["Base", "User", "Tweet", "Media", "Like", "Follow", "tweet_media_association_table"]
