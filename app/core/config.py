import os

from dotenv import load_dotenv
from pydantic import BaseSettings, PostgresDsn

# Загружаем переменные из .env
load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Microblog API"

    # БД
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "microblog_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "microblog_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "microblog_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))

    DATABASE_URL: PostgresDsn = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    # API токен (для авторизации)
    API_KEY: str = os.getenv("API_KEY", "super_secret_key")

    # Максимальная длина твита (символов)
    TWEET_MAX_LENGTH: int = os.getenv("TWEET_MAX_LENGTH", 280)

    # Настройки для дебаггинга
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Настройки для тестов
    TESTING: bool = os.getenv("TESTING", "false").lower() == "true"
    TEST_DB_URL: str = os.getenv("TEST_DB_URL", "sqlite:///./test.db")

    class Config:
        env_file = ".env"


settings = Settings()
