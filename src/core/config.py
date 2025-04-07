"""Конфигурация приложения."""

from functools import cached_property
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Основные настройки приложения."""
    # --- Статические настройки ---
    # Название приложения
    PROJECT_NAME: str = "Microblog Service"
    # Версия API
    API_VERSION: str = "1.0.0"
    # Префикс v1 роутера
    API_V1_STR: str = "/api/v1"
    # Путь внутри контейнера к медиа-папке
    STORAGE_PATH: Path = Path("/app/src/static/media")
    # Разрешенные типы контента для загружаемых медиа
    ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif"]
    # URL-префикс для доступа к медиа через FastAPI/Nginx
    MEDIA_URL_PREFIX: str = "/static/media"
    # Уровень логирования
    LOG_LEVEL: str = "INFO"

    # --- Настройки, читаемые из .env ---
    # Настройки базы данных
    POSTGRES_USER: str = Field(..., description="Имя пользователя PostgreSQL")
    POSTGRES_PASSWORD: str = Field(..., description="Пароль PostgreSQL")
    POSTGRES_DB: str = Field(..., description="Имя базы данных")
    POSTGRES_HOST: str = Field("db", description="Хост PostgreSQL (имя сервиса в Docker)")
    POSTGRES_PORT: int = Field(5432, description="Порт PostgreSQL")

    # Настройки режимов приложения
    DEBUG: bool = Field(default=False, description="Режим отладки")
    TESTING: bool = Field(default=False, description="Режим тестирования")

    # Настройки безопасности
    API_KEY_HEADER: str = Field("api-key", description="HTTP-заголовок с API-ключом")
    SECRET_KEY: str = Field(..., description="Секретный API-ключ")

    # --- Вычисляемые поля ---
    # Продакшен режим
    @computed_field
    @cached_property
    def PRODUCTION(self) -> bool:
        # Считаем продакшеном, если не DEBUG и не TESTING
        return not self.DEBUG and not self.TESTING

    # Путь внутри контейнера к папке с файлом лога
    @computed_field
    @cached_property
    def LOG_FILE(self) -> Path | None:
        # Если включен PRODUCTION, то логгируем в файл
        return Path("/app/src/logs/app.log") if self.PRODUCTION else None

    # Формируем URL БД
    @computed_field(repr=False)
    @cached_property
    def DATABASE_URL(self) -> str:
        """URL для БД основной или тестовой."""
        return "sqlite+aiosqlite:///./test.db" if self.TESTING else (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Имена переменных окружения чувствительны к регистру
        extra="ignore",  # Игнорировать лишние переменные окружения
    )


# Кэшированный экземпляр настроек
settings = Settings()
