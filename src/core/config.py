"""Конфигурация приложения."""

from functools import cached_property

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
    # Уровень логирования
    LOG_LEVEL: str = "INFO"
    # Путь внутри контейнера к папке с логами (создается в Dockerfile)
    LOG_FILE_PATH: str = "/app/src/logs/app.log"
    # Путь внутри контейнера к медиа-папке (создается в Dockerfile)
    STORAGE_PATH: str = "/app/src/static/media"
    # URL-префикс для доступа к медиа через FastAPI/Nginx
    MEDIA_URL_PREFIX: str = "/static/media"

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

    #
    @computed_field(repr=False)
    @cached_property
    def DATABASE_URL(self) -> str:
        """URL для основной PostgreSQL БД."""
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")

    @computed_field
    @cached_property
    def EFFECTIVE_DATABASE_URL(self) -> str:
        """Актуальный URL базы данных (тестовой или основной)."""
        return "sqlite+aiosqlite:///./test.db" if self.TESTING else self.DATABASE_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Имена переменных окружения чувствительны к регистру
        extra="ignore",  # Игнорировать лишние переменные окружения
    )


# Кэшированный экземпляр настроек
settings = Settings()
