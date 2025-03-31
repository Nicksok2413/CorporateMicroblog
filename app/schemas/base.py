"""Базовые схемы для всех моделей."""

from pydantic import BaseModel
from datetime import datetime


class BaseSchema(BaseModel):
    """Базовая схема с общими настройками."""

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }