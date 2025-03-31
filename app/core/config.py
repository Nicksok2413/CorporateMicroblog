from functools import cached_property
from pathlib import Path

from pydantic import AnyUrl, Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Основные настройки приложения.

    Attributes:
        DEBUG: Режим отладки
        TESTING: Режим тестирования
        PRODUCTION: Продакшен режим
    """

    # Настройки приложения
    DEBUG: bool = Field(default=False, description="Режим отладки")
    TESTING: bool = Field(default=False, description="Режим тестирования")
    PRODUCTION: bool = Field(default=False, description="Продакшен режим")

    # Настройки базы данных
    POSTGRES_USER: str = Field(..., description="Имя пользователя PostgreSQL")
    POSTGRES_PASSWORD: str = Field(..., description="Пароль PostgreSQL")
    POSTGRES_DB: str = Field(..., description="Имя базы данных")
    POSTGRES_HOST: str = Field("localhost", description="Хост PostgreSQL")
    POSTGRES_PORT: int = Field(5432, description="Порт PostgreSQL")
    TEST_DB_URL: AnyUrl = Field("sqlite:///./test.db", description="URL тестовой БД")

    # Настройки безопасности
    API_KEY_HEADER: str = Field("api-key", description="HTTP-заголовок с API-ключом")
    SECRET_KEY: str = Field(..., min_length=32, description="Секретный ключ")

    # Настройки логгирования
    LOG_LEVEL: str = Field("INFO", description="Уровень логирования")
    LOG_FILE: Path | None = Field(None, description="Файл для записи логов")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @computed_field
    @cached_property
    def DATABASE_URL(self) -> PostgresDsn:
        """Динамически генерируемый DSN для PostgreSQL.

        Returns:
            PostgresDsn: Строка подключения
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB
        )

    def model_post_init(self, __context) -> None:
        """Пост-инициализация модели.

        Args:
            __context: Контекст инициализации
        """
        if self.LOG_FILE:
            self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# Кэшированный экземпляр настроек
settings = Settings()