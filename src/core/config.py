"""Конфигурация приложения."""

from functools import cached_property
from pathlib import Path
from tempfile import gettempdir

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Основные настройки приложения."""
    # --- Статические настройки ---
    # Название приложения
    PROJECT_NAME: str = "Microblog Service"
    # Версия API
    API_VERSION: str = "1.0.0"
    # URL-префикс для доступа к медиа через FastAPI/Nginx
    MEDIA_URL_PREFIX: str = "/media"

    # --- Настройки, читаемые из .env ---
    # Настройки БД
    POSTGRES_USER: str = Field(..., description="Имя пользователя PostgreSQL")
    POSTGRES_PASSWORD: str = Field(..., description="Пароль PostgreSQL")
    POSTGRES_DB: str = Field(..., description="Имя базы данных")
    POSTGRES_HOST: str = Field("db", description="Хост PostgreSQL (имя сервиса в Docker)")
    POSTGRES_PORT: int = Field(5432, description="Порт PostgreSQL")
    # Настройки режимов приложения
    DEBUG: bool = Field(default=False, description="Режим отладки")
    TESTING: bool = Field(default=False, description="Режим тестирования")
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    # Настройки безопасности
    API_KEY_HEADER: str = Field("api-key", description="HTTP-заголовок с API-ключом")

    # --- Вычисляемые поля ---
    # Продакшен режим
    @computed_field
    @cached_property
    def PRODUCTION(self) -> bool:
        # Считаем продакшеном, если не DEBUG и не TESTING
        return not self.DEBUG and not self.TESTING

    # Формируем URL БД
    @computed_field(repr=False)
    @cached_property
    def DATABASE_URL(self) -> str:
        """URL для БД основной или тестовой."""
        if self.TESTING:
            # Используем SQLite in-memory для тестов
            # Чтобы одна и та же БД использовалась в рамках сессии pytest добавляем "?cache=shared" и "&uri=true"
            return "sqlite+aiosqlite:///:memory:?cache=shared&uri=true"
        else:
            return (
                f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

    # Путь к папке для хранения загруженных медиафайлов
    @computed_field
    @cached_property
    def MEDIA_ROOT_PATH(self) -> Path:
        if self.TESTING:
            # Используем временную директорию системы, если TESTING=True
            temp_media_path = Path(gettempdir()) / "temp_media"
            temp_media_path.mkdir(parents=True, exist_ok=True)
            return temp_media_path
        else:
            # Путь внутри Docker-контейнера
            return Path("/media")

    # Путь к папке для хранения лог-файлов
    @computed_field
    @cached_property
    def LOG_ROOT_PATH(self) -> Path:
        # Используем временную директорию системы, если TESTING=True
        if self.TESTING:
            temp_log_path = Path(gettempdir()) / "temp_logs"
            temp_log_path.mkdir(parents=True, exist_ok=True)
            return temp_log_path
        else:
            # Путь внутри Docker-контейнера
            return Path("/logs")

    # Путь внутри контейнера к файлу лога
    @computed_field
    @cached_property
    def LOG_FILE_PATH(self) -> Path | None:
        # Пишем в файл только в production режиме
        # Файл будет находиться в volume, смонтированном в LOG_ROOT_PATH
        return self.LOG_ROOT_PATH / "app.log" if self.PRODUCTION else None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Имена переменных окружения чувствительны к регистру
        extra="ignore",  # Игнорировать лишние переменные окружения
    )


# Кэшированный экземпляр настроек
settings = Settings()
