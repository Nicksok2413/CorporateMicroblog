"""Базовые схемы Pydantic, используемые в приложении."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class TunedModel(BaseModel):
    """
    Базовая модель Pydantic с настройками для работы с ORM.

    Включает `from_attributes=True` для преобразования объектов SQLAlchemy в схемы.
    """
    model_config = ConfigDict(from_attributes=True)


class ResultTrue(BaseModel):
    """
    Стандартная схема для успешного ответа без дополнительных данных.

    Fields:
        result (bool): Всегда True для этой схемы.
    """
    result: bool = True


class ResultFalseWithError(BaseModel):
    """
    Стандартная схема для ответа об ошибке.

    Fields:
        result (bool): Всегда False для этой схемы.
        error_type (str): Строковый идентификатор типа ошибки.
        error_message (Any): Сообщение или детали ошибки.
        extra_info (Optional[Dict[str, Any]]): Дополнительная информация об ошибке (опционально).
    """
    result: bool = False
    error_type: str
    error_message: Any  # Может быть строкой или сложной структурой (например, ошибки валидации)
    extra_info: Optional[Dict[str, Any]] = None  # Для передачи доп. данных из исключений
