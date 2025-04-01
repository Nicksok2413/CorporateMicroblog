"""Базовый репозиторий."""

from typing import TypeVar, Generic

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый класс для репозиториев."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, obj_id: int) -> ModelType | None:
        """Находит объект по ID.

        Args:
            obj_id: Идентификатор объекта

        Returns:
            ModelType | None: Объект или None
        """
        result = await self.session.execute(select(self.model).filter_by(id=obj_id))
        return result.scalar_one_or_none()
