"""Pydantic-схемы для медиафайлов."""

from pydantic import BaseModel


class MediaResponse(BaseModel):
    """Схема ответа с информацией о медиафайле.

    Fields:
        id: ID файла в БД
        url: Относительный URL файла
    """
    id: int
    url: str
