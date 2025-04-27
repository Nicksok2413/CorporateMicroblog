"""Репозиторий для работы с моделью User."""

from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(
    BaseRepository[User, BaseModel]
):  # Используем BaseModel как тип-заглушку
    """
    Репозиторий для выполнения CRUD операций с моделью User.

    Использует хешированные API ключи.
    """

    async def get_by_sha256(
        self, db: AsyncSession, *, sha256_hash: str
    ) -> Optional[User]:
        """
        Ищет пользователя по SHA256 хешу его API ключа.

        Args:
            db (AsyncSession): Сессия БД.
            sha256_hash (str): SHA256 хеш ключа.

        Returns:
            Optional[User]: Найденный пользователь или None.
        """
        statement = select(self.model).where(self.model.api_key_sha256 == sha256_hash)
        result = await db.execute(statement)
        return result.scalars().first()
