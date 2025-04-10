import os
import sys
# from dotenv import load_dotenv
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import URL

from alembic import context

# Импортируем базовую модель SQLAlchemy
from src.models.base import Base

# Импортируем все модели, чтобы они зарегистрировались в Base.metadata
# noqa: F401 нужен, чтобы линтеры не ругались на неиспользуемый импорт, хотя он критически важен для Alembic.
import src.models  # noqa: F401 (Импорт нужен для регистрации моделей)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Добавляем корневую директорию проекта в sys.path, чтобы можно было импортировать из 'src'
# Предполагаем, что env.py находится в alembic/, а src/ рядом с alembic/
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

# Загружаем переменные из .env файла
# dotenv_path = os.path.join(project_dir, '.env')
# if os.path.exists(dotenv_path):
#     load_dotenv(dotenv_path)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Читает переменные окружения и формирует объект URL для SQLAlchemy."""
    user = os.getenv("POSTGRES_USER", "default_user")
    password = os.getenv("POSTGRES_PASSWORD", "default_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", 5432)
    db_name = os.getenv("POSTGRES_DB", "default_db")

    db_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
    # --- ОТЛАДОЧНЫЙ ВЫВОД ---
    # Выводим в stderr, чтобы точно увидеть в логах Docker
    print(f"DEBUG [env.py]: Trying to connect - {db_url}...", file=sys.stderr)
    # --- КОНЕЦ ОТЛАДОЧНОГО ВЫВОДА ---

    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = "postgresql+psycopg://microblog_user:secure_password@db:5432/microblog_db"
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Собираем конфигурацию движка, исключая sqlalchemy.url
    engine_config = config.get_section(config.config_ini_section, {})
    db_url_object = get_database_url()
    engine_config["sqlalchemy.url"] = str(db_url_object)

    connectable = engine_from_config(
        engine_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
