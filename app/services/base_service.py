"""Базовый класс для сервисов."""

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.base import Base
from app.repositories.base import BaseRepository

# Определяем Generic типы
ModelType = TypeVar("ModelType", bound=Base)
RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepoType]):
    """
    Базовый сервис.

    Предоставляет доступ к ассоциированному репозиторию.
    Может содержать общую логику для всех сервисов, если такая появится.

    Args:
        repo (RepoType): Экземпляр репозитория, соответствующий модели сервиса.
    """

    def __init__(self, repo: RepoType):
        self.repo = repo

    async def _get_obj_or_404(self, db: AsyncSession, *, obj_id: int) -> ModelType:
        """
        Вспомогательный метод для получения объекта по ID или выброса NotFoundError.

        Args:
            db (AsyncSession): Сессия БД.
            obj_id (int): ID объекта.

        Returns:
            ModelType: Найденный объект.

        Raises:
            NotFoundError: Если объект не найден.
        """
        obj = await self.repo.get(db, obj_id=obj_id)

        if not obj:
            raise NotFoundError(f"{self.repo.model.__name__} с ID {obj_id} не найден.")

        return obj
