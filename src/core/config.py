"""Конфигурация приложения."""

from functools import cached_property
from pathlib import Path
from typing import Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Основные настройки приложения.

    Attributes:
        DEBUG: Режим отладки
        TESTING: Режим тестирования
        PRODUCTION: Продакшен режим
        POSTGRES_USER: Имя пользователя PostgreSQL
        POSTGRES_PASSWORD: Пароль PostgreSQL
        POSTGRES_DB: Имя базы данных
        POSTGRES_HOST: Хост PostgreSQL
        POSTGRES_PORT: Порт PostgreSQL
        STORAGE_PATH: Директория для хранения медиафайлов (строка)

        STORAGE_PATH_OBJ: Директория для хранения медиафайлов (Path объект)
        API_KEY_HEADER: HTTP-заголовок с API-ключом
        SECRET_KEY: Секретный ключ (минимум 32 символа)
        LOG_LEVEL: Уровень логирования
        LOG_FILE: Файл для записи логов (Path объект)
    """
    # --- Статические настройки ---
    # Название приложения
    PROJECT_NAME: str = "Microblog Service"
    # Версия API
    API_VERSION: str = "1.0.0"
    # Префикс v1 роутера
    API_V1_STR: str = "/api/v1"
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

    # Логирование
    LOG_LEVEL: str = Field("INFO", description="Уровень логирования")
    # LOG_FILE можно оставить в .env, если путь должен быть настраиваемым
    # Если путь всегда /src/src/logs/src.log, можно задать его здесь
    LOG_FILE_PATH_INSIDE_CONTAINER: Optional[str] = "/src/src/logs/src.log" # Пример статического пути

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

    @computed_field
    @cached_property
    def STORAGE_PATH(self) -> str:
         """Возвращает актуальный путь к хранилищу медиа."""
         # В режиме тестирования используем временную папку (лучше управлять через фикстуры)
         # В обычном режиме - путь внутри контейнера
         return "./test_media" if self.TESTING else STORAGE_PATH_INSIDE_CONTAINER

    # Настройки хранения файлов
    STORAGE_PATH: str = Field(
        "/src/static/media",  # Путь внутри контейнера
        description="Директория для хранения медиафайлов (строковое представление)"
    )

    # Это поле будет вычислено в model_post_init
    STORAGE_PATH_OBJ: Optional[Path] = Field(None, description="Объект Path для хранения медиафайлов", exclude=True)

    # Настройки логирования
    LOG_LEVEL: str = Field("INFO", description="Уровень логирования")
    LOG_FILE: Optional[Path] = Field("logs/src.log", description="Файл для записи логов")  # LOG_FILE теперь Path

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Имена переменных окружения чувствительны к регистру
        extra="ignore",  # Игнорировать лишние переменные окружения
    )


    @computed_field
    @cached_property
    def EFFECTIVE_STORAGE_PATH(self) -> str:
        return "./test_media" if self.TESTING else self.STORAGE_PATH


# Кэшированный экземпляр настроек
settings = Settings()
