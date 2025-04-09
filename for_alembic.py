# src/core/config.py
class Settings(BaseSettings):
    # ...
    POSTGRES_PORT: int = Field(5432, description="Порт PostgreSQL") # Возвращаем int
    # ...
    @computed_field(repr=False)
    @cached_property
    def DATABASE_URL(self) -> str:
        # Асинхронный URL для FastAPI
        return "sqlite+aiosqlite:///./test.db" if self.TESTING else (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- ДОБАВИМ ЯВНЫЙ СИНХРОННЫЙ URL для Alembic ---
    @computed_field(repr=False)
    @cached_property
    def SYNC_DATABASE_URL(self) -> str:
        """Синхронный URL для использования Alembic."""
        # Используем тот же драйвер psycopg, но без async префикса
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    # --------------------------------------------------
    # ... model_config ...
settings = Settings()
# ...

# alembic/env.py
import os
import sys
from logging.config import fileConfig

from alembic import context
# Убираем импорт create_engine и engine_from_config
from sqlalchemy import pool
# Импортируем ТОЛЬКО синхронный create_engine
from sqlalchemy import create_engine

# Добавляем корень проекта в sys.path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

# --- Импорт настроек Pydantic ---
try:
    from src.core.config import settings
    # Используем ЯВНО созданный синхронный URL
    db_url_for_alembic = settings.SYNC_DATABASE_URL
    print(f"Using database URL for Alembic: {'*' * 5}{db_url_for_alembic[-20:]}") # Лог для проверки
except ImportError as e:
    print(f"Error importing settings: {e}. Ensure src is in PYTHONPATH.")
    sys.exit(1)
except AttributeError:
    print("Error: SYNC_DATABASE_URL not found in settings. Check src/core/config.py")
    sys.exit(1)
# --------------------------------

# --- Импорт моделей ---
try:
    from src.models.base import Base
    import src.models  # noqa: F401
except ImportError as e:
    print(f"Error importing models: {e}. Ensure src is in PYTHONPATH and models exist.")
    sys.exit(1)
# ----------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=db_url_for_alembic, # <--- Используем URL из settings
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        # Создаем СИНХРОННЫЙ движок, используя URL из settings
        connectable = create_engine(db_url_for_alembic, poolclass=pool.NullPool)

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    except Exception as e:
        print(f"Error during online migration: {e}")
        raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


# alembic.ini
# ...
# sqlalchemy.url = postgresql+psycopg://${POSTGRES_USER}:... # Больше не нужно здесь
# ...