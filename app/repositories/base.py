"""Базовый класс репозитория с общими CRUD операциями."""

from typing import Any, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models.base import Base

# Определяем Generic типы для моделей SQLAlchemy и схем Pydantic
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType]):
    """
    Базовый репозиторий с асинхронными CRUD операциями.

    Args:
        model (Type[ModelType]): Класс модели SQLAlchemy.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, *, obj_id: Any) -> Optional[ModelType]:
        """
        Получает запись по её ID.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            obj_id (Any): Идентификатор записи.

        Returns:
            Optional[ModelType]: Найденный объект модели или None.
        """
        log.debug(f"Получение {self.model.__name__} по ID: {obj_id}")
        result = await db.execute(select(self.model).where(self.model.id == obj_id))
        instance = result.scalars().first()

        if instance:
            log.debug(f"{self.model.__name__} с ID {obj_id} найден.")
        else:
            log.debug(f"{self.model.__name__} с ID {obj_id} не найден.")

        return instance

    async def get_all(self, db: AsyncSession) -> List[ModelType]:
        """
        Получает список записей.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.

        Returns:
            List[ModelType]: Список объектов модели.
        """
        log.debug(f"Получение списка {self.model.__name__}")
        result = await db.execute(select(self.model))
        instances = result.scalars().all()
        log.debug(f"Найдено {len(instances)} записей {self.model.__name__}.")
        return list(instances)

    async def add(self, db: AsyncSession, *, db_obj: ModelType) -> ModelType:
        """
        Добавляет объект модели в сессию.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            db_obj (ModelType): Экземпляр модели для добавления.

        Returns:
            ModelType: Добавленный объект модели.
        """
        log.debug(f"Добавление {self.model.__name__} в сессию (ID: {getattr(db_obj, 'id', 'new')})")
        db.add(db_obj)
        return db_obj

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создает и добавляет новый объект в сессию на основе Pydantic схемы.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            obj_in (CreateSchemaType): Pydantic схема с данными для создания.

        Returns:
            ModelType: Созданный объект модели.
        """
        obj_in_data = obj_in.model_dump()
        log.debug(f"Подготовка к созданию {self.model.__name__} с данными: {obj_in_data}")
        db_obj = self.model(**obj_in_data)
        await self.add(db, db_obj=db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, db_obj: ModelType) -> None:
        """
        Помечает объект для удаления в сессии.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            db_obj (ModelType): Экземпляр модели для удаления.
        """
        log.debug(f"Пометка на удаление {self.model.__name__} (ID: {getattr(db_obj, 'id', 'N/A')})")
        await db.delete(db_obj)

    async def remove(self, db: AsyncSession, *, obj_id: Any) -> Optional[ModelType]:
        """
        Находит объект по ID и помечает объект для удаления в сессии.

        Args:
            db (AsyncSession): Асинхронная сессия SQLAlchemy.
            obj_id (Any): Идентификатор записи для удаления.

        Returns:
            Optional[ModelType]: Объект, помеченный для удаления, или None, если не найден.
        """
        log.debug(f"Подготовка к удалению {self.model.__name__} по ID: {obj_id}")
        obj = await self.get(db, obj_id=obj_id)

        if obj:
            await self.delete(db, db_obj=obj)
            log.debug(f"{self.model.__name__} с ID {obj_id} помечен для удаления.")
            return obj
        else:
            log.warning(f"{self.model.__name__} с ID {obj_id} не найден для удаления.")
            return None
