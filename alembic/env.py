import os
import sys
# from dotenv import load_dotenv
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import URL

from alembic import context

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

# Импортируем базовую модель SQLAlchemy
from src.models.base import Base

# Импортируем все модели, чтобы они зарегистрировались в Base.metadata
# noqa: F401 нужен, чтобы линтеры не ругались на неиспользуемый импорт, хотя он критически важен для Alembic.
import src.models  # noqa: F401 (Импорт нужен для регистрации моделей)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> URL:
    """Читает переменные окружения и формирует объект URL для SQLAlchemy."""
    user = os.getenv("POSTGRES_USER", "default_user")
    password = os.getenv("POSTGRES_PASSWORD", "default_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "default_db")

    # --- ОТЛАДОЧНЫЙ ВЫВОД ---
    # Выводим в stderr, чтобы точно увидеть в логах Docker
    print(
        f"DEBUG [env.py]: Trying to connect with User='{user}', Password='{'*' * len(password) if password else 'None'}' (Actual retrieved: '{password}'), Host='{host}', Port='{port}', DB='{db_name}'",
        file=sys.stderr)
    # --- КОНЕЦ ОТЛАДОЧНОГО ВЫВОДА ---

    # Валидация порта (Alembic упадет здесь, если порт не числовой)
    try:
        int(port)
    except ValueError as exc:
        raise ValueError(f"Переменная окружения POSTGRES_PORT ('{port}') должна быть числом.") from exc

    return URL.create(
        drivername="postgresql+psycopg",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=db_name,
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
