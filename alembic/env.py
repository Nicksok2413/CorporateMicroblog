import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine

# --- Загрузка .env ---
from dotenv import load_dotenv
# Ищем .env на один уровень выше папки alembic (в корне проекта)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    print(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f".env file not found at: {dotenv_path}. Relying on existing environment variables.")

# Добавляем корень проекта в sys.path, чтобы найти app.*
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

# --- Импорт моделей ---
# Импортируем базовую модель SQLAlchemy
from app.models.base import Base
# Импортируем все модели, чтобы Alembic их обнаружил
from app.models.associations import tweet_media_association_table
from app.models.follow import Follow
from app.models.like import Like
from app.models.media import Media
from app.models.tweet import Tweet
from app.models.user import User

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Вспомогательная функция для запуска миграций с заданным соединением."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # include_schemas=True, # Раскомментировать, если используются схемы PostgreSQL
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запускает миграции в 'online' режиме, обрабатывая синхронное соединение."""
    # Получаем объект соединения из атрибутов конфигурации, если он был передан
    # (например, при интеграции с FastAPI/Starlette)
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        # Если внешнее соединение не передано (стандартный запуск alembic cli),
        # создаем СИНХРОННЫЙ движок из URL в alembic.ini
        try:
            connectable = create_engine(
                config.get_main_option("sqlalchemy.url"),  # Берем URL из ini
                poolclass=pool.NullPool  # Используем NullPool для CLI операций
            )
        except Exception as exc:
            print(f"Error creating engine from sqlalchemy.url: {exc}")
            print(f"URL used: {config.get_main_option('sqlalchemy.url')}")
            raise

    # Проверяем тип соединения/движка
    # Асинхронный путь (если бы мы передавали AsyncEngine в атрибуты config) - маловероятно для CLI
    if hasattr(connectable, 'run_sync'):  # Простой способ проверить на AsyncConnection/AsyncEngine
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    else:
        # Синхронный путь (стандартный для CLI)
        with connectable.connect() as connection:
            do_run_migrations(connection)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Запускаем асинхронную обертку для выполнения миграций
    try:
        asyncio.run(run_async_migrations())
    except Exception as exc:
        print(f"Error running online migrations: {exc}")
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
