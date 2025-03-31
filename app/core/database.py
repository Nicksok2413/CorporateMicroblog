from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import log


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class Database:
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def connect(self, **kwargs):
        """Установка подключения к БД с дополнительными параметрами"""
        self.engine = create_async_engine(
            # Используем тестовую БД если в настройках включен режим тестирования
            settings.TEST_DB_URL if settings.TESTING else settings.DATABASE_URL,
            echo=settings.DEBUG,  # Логирование SQL-запросов
            future=True,  # Включение нового стиля использования SQLAlchemy
            pool_pre_ping=True,
            **kwargs
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        await self._verify_connection()

    async def disconnect(self):
        """Корректное закрытие подключения"""
        if self.engine:
            await self.engine.dispose()
            log.success("Database connection closed")
            self.engine = None
            self.session_factory = None

    async def _verify_connection(self):
        """Проверка доступности БД"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            log.success("Database connection established")
        except Exception as exc:
            log.critical(f"Database connection failed: {exc}")
            raise

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.session_factory:
            raise RuntimeError("Database is not initialized")
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                log.error(f"Session rollback due to error: {e}")
                raise


# Глобальный экземпляр
db = Database()


# Dependency для FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор сессий для DI FastAPI.
    Использование:
    @router.get("/")
    async def endpoint(session: AsyncSession = Depends(get_db)):
        ...
    """
    async with db.session() as session:
        yield session


# Инициализация БД (для Alembic миграций)
async def init_db():
    """
    Инициализация БД (создание таблиц).
    Используется Alembic, но может быть полезно для тестов.
    """
    if not db.engine:
        await db.connect()

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    log.info("Database tables initialized")
