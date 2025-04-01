"""Базовый сервис."""

from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ServiceType = TypeVar("ServiceType")


class BaseService:
    """Базовый класс для сервисов."""

    def __init__(self, db: AsyncSession):
        self.db = db