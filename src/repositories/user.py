"""Репозиторий для работы с моделью User."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, None]):
    """
    Репозиторий для выполнения CRUD операций с моделью User.

    Наследует общие методы от BaseRepository и добавляет специфичные для User.
    """

    async def get_by_api_key(self, db: AsyncSession, *, api_key: str) -> Optional[User]:
        """
        Получает пользователя по его API ключу.

        Args:
            db (AsyncSession): Сессия БД.
            api_key (str): API ключ пользователя.

        Returns:
            Optional[User]: Найденный пользователь или None.
        """
        result = await db.execute(select(self.model).where(self.model.api_key == api_key))
        return result.scalars().first()
