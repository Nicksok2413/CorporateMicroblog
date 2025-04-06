"""Базовое определение модели для SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для декларативных моделей SQLAlchemy."""
    pass
