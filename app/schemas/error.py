"""Схемы для обработки ошибок."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Стандартная схема ошибки API."""

    result: bool = False
    error_type: str
    error_message: str

    class Config:
        json_schema_extra = {
            "example": {
                "result": False,
                "error_type": "not_found",
                "error_message": "Твит не найден"
            }
        }
