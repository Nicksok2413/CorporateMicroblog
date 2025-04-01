"""Базовый класс для сервисов."""

from typing import Generic, TypeVar

from app.repositories.base import BaseRepository  # Импортируем базовый репозиторий
from app.models.base import Base
from app.schemas.base import BaseModel

# Определяем Generic типы
ModelType = TypeVar("ModelType", bound=Base)
RepoType = TypeVar("RepoType", bound=BaseRepository)


# CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
# UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
# Схемы в базовом сервисе могут быть не так полезны, как в репозитории

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

    # Здесь можно добавить общие методы, например:
    # async def get_or_404(self, db: AsyncSession, id: Any) -> ModelType:
    #     """Получает объект по ID или вызывает исключение NotFoundError."""
    #     obj = await self.repo.get(db, id)
    #     if not obj:
    #         # Импортируем исключение здесь или передаем фабрику исключений
    #         from app.core.exceptions import NotFoundError
    #         raise NotFoundError(f"{self.repo.model.__name__} с ID {id} не найден.")
    #     return obj

    # Однако, такая логика часто лучше реализуется непосредственно
    # в конкретных методах сервисов, где контекст ошибки более понятен.
