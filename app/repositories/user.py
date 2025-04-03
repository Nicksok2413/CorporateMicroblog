"""Репозиторий для работы с моделью User."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, None, None]):
    """
    Репозиторий для выполнения CRUD операций с моделью User.

    Наследует общие методы от BaseRepository и добавляет специфичные для User.
    """

    async def get_by_api_key(self, db: AsyncSession, *, api_key: str) -> Optional[User]:
        """
        Получает пользователя по его API ключу.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            api_key: API ключ пользователя.

        Returns:
            Optional[User]: Найденный пользователь или None.
        """
        result = await db.execute(select(self.model).where(self.model.api_key == api_key))
        return result.scalars().first()


# Создаем экземпляр репозитория для использования в других частях приложения
user_repo = UserRepository(User)
