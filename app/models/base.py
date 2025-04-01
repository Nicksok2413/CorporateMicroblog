"""Базовое определение модели для SQLAlchemy."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Базовый класс для декларативных моделей SQLAlchemy.

    Включает метаданные с соглашением об именовании для ограничений и индексов БД.
    """
    metadata = MetaData(naming_convention=convention)
