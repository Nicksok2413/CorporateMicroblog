"""Схемы Pydantic для модели Media."""

from pydantic import Field

from app.schemas.base import ResultTrue, TunedModel, BaseModel


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


# --- Схема для представления Media (если понадобится в других ответах) ---
class MediaOut(TunedModel):
    """
    Схема для представления информации о медиафайле.

    Fields:
        id (int): ID медиафайла
        url (str): Ссылка на медиафайл
    """
    id: int
    url: str  # Поле URL будет формироваться в сервисе или эндпоинте
