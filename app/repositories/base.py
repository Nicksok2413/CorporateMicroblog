"""Базовый класс репозитория с общими CRUD операциями."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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
        model: Класс модели SQLAlchemy.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, obj_id: Any) -> Optional[ModelType]:
        """
        Получает запись по её ID.

        Args:
            db: Асинхронная сессия SQLAlchemy
            obj_id: Идентификатор записи

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

    async def get_multi(
            self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        Получает список записей с пагинацией.

        Args:
            db: Асинхронная сессия SQLAlchemy
            skip: Количество записей для пропуска
            limit: Максимальное количество записей для возврата

        Returns:
            List[ModelType]: Список объектов модели.
        """
        log.debug(f"Получение списка {self.model.__name__} (skip={skip}, limit={limit})")
        statement = select(self.model).offset(skip).limit(limit)
        result = await db.execute(statement)
        instances = result.scalars().all()
        log.debug(f"Найдено {len(instances)} записей {self.model.__name__}.")
        return instances

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создает новую запись в базе данных.

        Args:
            db: Асинхронная сессия SQLAlchemy
            obj_in: Pydantic схема с данными для создания

        Returns:
            ModelType: Созданный объект модели.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных при создании.
        """
        # Используем model_dump() для Pydantic V2
        obj_in_data = obj_in.model_dump()
        log.debug(f"Создание нового {self.model.__name__} с данными: {obj_in_data}")
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        try:
            await db.commit()
            await db.refresh(db_obj)
            log.info(f"Успешно создан {self.model.__name__} с ID: {db_obj.id}")
            return db_obj
        except IntegrityError as exc:
            await db.rollback()
            log.error(f"Ошибка целостности при создании {self.model.__name__}: {exc}")
            raise exc  # Передаем исключение дальше для обработки в сервисе/API
        except SQLAlchemyError as exc:
            await db.rollback()
            log.error(f"Ошибка БД при создании {self.model.__name__}: {exc}")
            raise exc

    async def update(
            self,
            db: AsyncSession,
            *,
            db_obj: ModelType,
            obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Обновляет существующую запись в базе данных.

        Args:
            db: Асинхронная сессия SQLAlchemy
            db_obj: Объект модели SQLAlchemy для обновления
            obj_in: Pydantic схема или словарь с данными для обновления

        Returns:
            ModelType: Обновленный объект модели.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных при обновлении.
        """
        # Используем model_dump() для Pydantic V2
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # exclude_unset=True - обновляем только переданные поля
            update_data = obj_in.model_dump(exclude_unset=True)

        log.debug(f"Обновление {self.model.__name__} с ID {db_obj.id}. Данные: {update_data}")
        if not update_data:
            log.warning(f"Нет данных для обновления {self.model.__name__} с ID {db_obj.id}")
            return db_obj  # Возвращаем без изменений, если нет данных

        # Обновляем поля объекта модели
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            else:
                log.warning(f"Попытка обновить несуществующее поле '{field}' в {self.model.__name__}")

        db.add(db_obj)  # Добавляем объект в сессию (на случай, если он был отсоединен)
        try:
            await db.commit()
            await db.refresh(db_obj)
            log.info(f"Успешно обновлен {self.model.__name__} с ID: {db_obj.id}")
            return db_obj
        except IntegrityError as exc:
            await db.rollback()
            log.error(f"Ошибка целостности при обновлении {self.model.__name__} (ID: {db_obj.id}): {exc}")
            raise exc
        except SQLAlchemyError as exc:
            await db.rollback()
            log.error(f"Ошибка БД при обновлении {self.model.__name__} (ID: {db_obj.id}): {exc}")
            raise exc

    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """
        Удаляет запись по её ID.

        Args:
            db: Асинхронная сессия SQLAlchemy
            id: Идентификатор записи для удаления

        Returns:
            Optional[ModelType]: Удаленный объект модели или None, если не найден.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных при удалении.
        """
        log.debug(f"Удаление {self.model.__name__} по ID: {id}")
        obj = await self.get(db, obj_id=id)
        if obj:
            try:
                await db.delete(obj)
                await db.commit()
                log.info(f"Успешно удален {self.model.__name__} с ID: {id}")
                return obj
            except IntegrityError as exc:
                # Это маловероятно при удалении, но возможно при сложных каскадах
                await db.rollback()
                log.error(f"Ошибка целостности при удалении {self.model.__name__} (ID: {id}): {exc}")
                raise exc
            except SQLAlchemyError as exc:
                await db.rollback()
                log.error(f"Ошибка БД при удалении {self.model.__name__} (ID: {id}): {exc}")
                raise exc
        else:
            log.warning(f"{self.model.__name__} с ID {id} не найден для удаления.")
            return None

    async def count(self, db: AsyncSession) -> int:
        """
        Подсчитывает общее количество записей данной модели.

        Args:
            db: Асинхронная сессия SQLAlchemy.

        Returns:
            int: Общее количество записей.
        """
        log.debug(f"Подсчет общего количества {self.model.__name__}")
        statement = select(func.count()).select_from(self.model)
        result = await db.execute(statement)
        count = result.scalar_one()
        log.debug(f"Общее количество {self.model.__name__}: {count}")
        return count
