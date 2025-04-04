"""Конфигурация приложения."""

from functools import cached_property
from pathlib import Path
from typing import Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import log


class Settings(BaseSettings):
    """
    Основные настройки приложения.

    Attributes:
        PROJECT_NAME: Название приложения
        API_VERSION: Версия приложения
        API_V1_STR: ? Префикс v1 роутера ?
        DEBUG: Режим отладки
        TESTING: Режим тестирования
        PRODUCTION: Продакшен режим
        POSTGRES_USER: Имя пользователя PostgreSQL
        POSTGRES_PASSWORD: Пароль PostgreSQL
        POSTGRES_DB: Имя базы данных
        POSTGRES_HOST: Хост PostgreSQL
        POSTGRES_PORT: Порт PostgreSQL
        TEST_DB_URL: URL тестовой БД (SQLite по умолчанию)
        STORAGE_PATH: Директория для хранения медиафайлов (строка)
        MEDIA_URL_PREFIX: Префикс URL для доступа к медиафайлам через статику FastAPI/Nginx
        STORAGE_PATH_OBJ: Директория для хранения медиафайлов (Path объект)
        API_KEY_HEADER: HTTP-заголовок с API-ключом
        SECRET_KEY: Секретный ключ (минимум 32 символа)
        LOG_LEVEL: Уровень логирования
        LOG_FILE: Файл для записи логов (Path объект)
    """
    # Настройки приложения
    PROJECT_NAME: str = Field(..., description="Название приложения")
    API_VERSION: str = Field(..., description="Версия приложения")
    API_V1_STR: str = Field(..., description="? Префикс v1 роутера ?")

    # Настройки базы данных
    POSTGRES_USER: str = Field(..., description="Имя пользователя PostgreSQL")
    POSTGRES_PASSWORD: str = Field(..., description="Пароль PostgreSQL")
    POSTGRES_DB: str = Field(..., description="Имя базы данных")
    POSTGRES_HOST: str = Field("db", description="Хост PostgreSQL (имя сервиса в Docker)")
    POSTGRES_PORT: int = Field(5432, description="Порт PostgreSQL")
    TEST_DB_URL: str = Field("sqlite+aiosqlite:///./test.db", description="URL тестовой БД (Async SQLite)")

    # Настройки режимов приложения
    DEBUG: bool = Field(default=False, description="Режим отладки")
    TESTING: bool = Field(default=False, description="Режим тестирования")
    PRODUCTION: bool = Field(default=True, description="Продакшен режим")  # По умолчанию продакшен

    # Настройки хранения файлов
    STORAGE_PATH: str = Field(
        "/app/static/media",  # Путь внутри контейнера
        description="Директория для хранения медиафайлов (строковое представление)"
    )
    MEDIA_URL_PREFIX: str = Field(
        "/static/media",
        description="Префикс URL для доступа к медиафайлам через статику FastAPI/Nginx"
    )
    # Это поле будет вычислено в model_post_init
    STORAGE_PATH_OBJ: Optional[Path] = Field(None, description="Объект Path для хранения медиафайлов", exclude=True)

    # Настройки безопасности
    API_KEY_HEADER: str = Field("api-key", description="HTTP-заголовок с API-ключом")
    SECRET_KEY: str = Field(..., description="Секретный API-ключ")

    # Настройки логирования
    LOG_LEVEL: str = Field("INFO", description="Уровень логирования")
    LOG_FILE: Optional[Path] = Field(None, description="Файл для записи логов")  # LOG_FILE теперь Path

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Имена переменных окружения чувствительны к регистру
        extra="ignore",  # Игнорировать лишние переменные окружения
    )

    @computed_field(repr=False)  # Скрываем из стандартного вывода repr, так как содержит пароль
    @cached_property
    def DATABASE_URL(self) -> str:
        """
        Динамически генерируемый URL для PostgreSQL.

        Returns:
            str: Строка подключения к основной БД.
        """
        db_url = (f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                  f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")
        return db_url

    @computed_field
    @cached_property
    def EFFECTIVE_DATABASE_URL(self) -> str:
        """
        Возвращает актуальный URL базы данных в зависимости от режима TESTING.

        Returns:
            str: Строка подключения к БД (тестовой или основной).
        """
        return self.TEST_DB_URL if self.TESTING else self.DATABASE_URL

    @computed_field
    @cached_property
    def EFFECTIVE_STORAGE_PATH(self) -> str:
        return "./test_media" if self.TESTING else self.STORAGE_PATH

    def model_post_init(self, __context) -> None:
        """
        Пост-инициализация модели для создания директорий.

        Args:
            __context: Контекст инициализации.
        """
        effective_path_str = self.EFFECTIVE_STORAGE_PATH
        self.STORAGE_PATH_OBJ = Path(effective_path_str)

        try:
            self.STORAGE_PATH_OBJ.mkdir(parents=True, exist_ok=True)
            log.info(f"Создана директория: {self.STORAGE_PATH_OBJ}")
        except OSError as exc:
            log.error(f"Не удалось создать директорию {self.STORAGE_PATH_OBJ}: {exc}")

        # Создаем директорию логов, если LOG_FILE задан
        if self.LOG_FILE:
            if isinstance(self.LOG_FILE, str):  # На всякий случай
                self.LOG_FILE = Path(self.LOG_FILE)
            try:
                self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                log.error(f"Не удалось создать директорию для лог-файла {self.LOG_FILE.parent}: {exc}")


# Кэшированный экземпляр настроек
settings = Settings()
