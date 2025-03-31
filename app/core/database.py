from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Асинхронный движок подключения
engine = create_async_engine(
    # Используем тестовую БД если в настройках включен режим тестирования
    settings.TEST_DB_URL if settings.TESTING else settings.DATABASE_URL,
    echo=settings.DEBUG,  # Логирование SQL-запросов
    future=True  # Включение нового стиля использования SQLAlchemy
)

# Фабрика для создания асинхронных сессий
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Данные остаются доступными после коммита
)


# Базовый класс для моделей
class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


# Dependency для FastAPI
async def get_db() -> AsyncSession:
    """Асинхронный генератор для получения сессии БД."""
    async with async_session_factory() as session:
        yield session


# Инициализация БД (для Alembic миграций)
async def init_db():
    """Создает таблицы в БД (используется для Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
