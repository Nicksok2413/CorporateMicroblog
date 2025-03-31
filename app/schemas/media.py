"""Pydantic-схемы для медиафайлов."""

from app.schemas.base import BaseSchema


class MediaResponse(BaseSchema):
    """Схема ответа с информацией о медиафайле.

    Fields:
        id: ID файла в БД
        url: Относительный URL файла
    """
    id: int
    url: str
