"""Схемы Pydantic для модели Media."""

from pydantic import Field

from src.schemas.base import BaseModel, ResultTrue


# --- Схема для создания (используется внутри приложения) ---
class MediaCreate(BaseModel):
    """
    Схема для создания записи Media в БД (внутреннее использование).

    Fields:
        file_path (str): Относительный путь к сохраненному файлу
    """

    file_path: str = Field(..., description="Относительный путь к файлу в хранилище")


# --- Схема для API ответа при загрузке ---
class MediaCreateResult(ResultTrue):
    """
    Схема ответа для эндпоинта загрузки медиафайла.

    Fields:
        result (bool): Всегда True
        media_id (int): ID загруженного и сохраненного медиафайла
    """

    media_id: int
