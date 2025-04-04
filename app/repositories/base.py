"""Базовый класс репозитория с общими CRUD операциями."""

from typing import Any, Generic, List, Optional, Type, TypeVar, Union, Dict

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models.base import Base

# Определяем Generic типы для моделей SQLAlchemy и схем Pydantic
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Базовый репозиторий с асинхронными CRUD операциями.

    Args:
        model (Type[ModelType]): Класс модели SQLAlchemy.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, obj_id: Any) -> Optional[ModelType]:
        """
        Получает запись по её ID.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            obj_id: Идентификатор записи.

        Returns:
            Optional[ModelType]: Найденный объект модели или None.
        """
        log.debug(f"Получение {self.model.__name__} по ID: {obj_id}")
        statement = select(self.model).where(self.model.id == obj_id)
        result = await db.execute(statement)
        instance = result.scalars().first()

        if instance:
            log.debug(f"{self.model.__name__} с ID {obj_id} найден.")
        else:
            log.debug(f"{self.model.__name__} с ID {obj_id} не найден.")
        return instance

    async def get_all(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Получает список записей с пагинацией.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            skip: Количество записей для пропуска.
            limit: Максимальное количество записей для возврата.

        Returns:
            List[ModelType]: Список объектов модели.
        """
        log.debug(f"Получение списка {self.model.__name__} (skip={skip}, limit={limit})")
        statement = select(self.model).offset(skip).limit(limit)
        result = await db.execute(statement)
        instances = result.scalars().all()
        log.debug(f"Найдено {len(instances)} записей {self.model.__name__}.")
        return list(instances)

    async def add(self, db: AsyncSession, *, db_obj: ModelType) -> ModelType:
        """
        Добавляет объект модели в сессию. Коммит должен быть вызван отдельно.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            db_obj: Экземпляр модели для добавления.

        Returns:
            ModelType: Добавленный объект модели.
        """
        log.debug(f"Добавление {self.model.__name__} в сессию (ID: {getattr(db_obj, 'id', 'new')})")
        db.add(db_obj)
        return db_obj

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создает и добавляет новый объект в сессию на основе Pydantic схемы.
        Коммит должен быть вызван отдельно.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            obj_in: Pydantic схема с данными для создания.

        Returns:
            ModelType: Созданный объект модели (еще не в БД).
        """
        obj_in_data = obj_in.model_dump()
        log.debug(f"Подготовка к созданию {self.model.__name__} с данными: {obj_in_data}")
        db_obj = self.model(**obj_in_data)
        await self.add(db, db_obj=db_obj)
        return db_obj

    async def update(
            self,
            db: AsyncSession,
            *,
            db_obj: ModelType,
            obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
         Обновляет атрибуты существующего объекта модели.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            db_obj: Объект модели SQLAlchemy для обновления.
            obj_in: Pydantic схема или словарь с данными для обновления.

        Returns:
            ModelType: Объект модели с обновленными атрибутами.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)  # exclude_unset=True - обновляем только переданные поля

        log.debug(f"Обновление {self.model.__name__} с ID {db_obj.id}. Данные: {update_data}")

        if not update_data:
            log.warning(f"Нет данных для обновления {self.model.__name__} с ID {db_obj.id}")
            return db_obj

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            else:
                log.warning(f"Попытка обновить несуществующее поле '{field}' в {self.model.__name__}")

        await self.add(db, db_obj=db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, obj_id: Any) -> Optional[ModelType]:
        """
        Помечает объект для удаления в сессии по его ID.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            obj_id: Идентификатор записи для удаления.

        Returns:
            Optional[ModelType]: Объект, помеченный для удаления, или None, если не найден.
        """
        log.debug(f"Подготовка к удалению {self.model.__name__} по ID: {obj_id}")
        obj = await self.get(db, obj_id=obj_id)
        if obj:
            await db.delete(obj)
            log.debug(f"{self.model.__name__} с ID {obj_id} помечен для удаления.")
            return obj
        else:
            log.warning(f"{self.model.__name__} с ID {obj_id} не найден для удаления.")
            return None
