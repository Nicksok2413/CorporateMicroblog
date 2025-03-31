"""Общие схемы ответов."""

from typing import TypeVar, Generic, List

from pydantic import BaseModel


T = TypeVar('T')


class SuccessResponse(BaseModel):
    """Стандартный успешный ответ."""
    result: bool = True


class PaginatedResponse(SuccessResponse, Generic[T]):
    """Схема для пагинированных ответов."""
    data: List[T]
    total: int
    page: int
    per_page: int