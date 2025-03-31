"""Модуль для работы с асинхронной PostgreSQL через SQLAlchemy.

Содержит:
- Настройку асинхронного движка БД
- Фабрику сессий
- Базовую модель ORM
- Утилиты для управления подключением
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import log


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей"""
    pass


class Database:
    """Менеджер подключений к базе данных.

        Отвечает за:
        - Инициализацию подключения
        - Управление пулом соединений
        - Создание сессий
        """

    def __init__(self):
        """Инициализирует менеджер с пустыми подключениями."""
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def connect(self, **kwargs):
        """Устанавливает подключение к базе данных.

        Args:
            **kwargs: Дополнительные параметры для create_async_engine

        Raises:
            RuntimeError: При неудачной проверке подключения
        """
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
        log.success("Подключение к базе данных установлено.")

    async def disconnect(self):
        """Корректное закрытие подключения"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            log.info("Подключение к базе данных закрыто.")

    async def _verify_connection(self):
        """Проверяет работоспособность подключения.

        Raises:
            RuntimeError: Если проверка подключения не удалась
        """
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            log.critical(f"Ошибка подключения к базе: {exc}")
            raise RuntimeError("Ошибка проверки подключения к БД") from exc

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Асинхронный контекстный менеджер для работы с сессиями.

        Yields:
            AsyncSession: Экземпляр сессии БД

        Raises:
            RuntimeError: При вызове до инициализации подключения
        """
        if not self.session_factory:
            raise RuntimeError("База не инициализирована. Сначала вызовите await db.connect()")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as exc:
                await session.rollback()
                log.error(f"Откат сессии: {type(exc).__name__}: {exc}")
                raise


# Глобальный экземпляр менеджера БД
db = Database()


# Dependency для FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency для инъекции сессий БД.

    Yields:
        AsyncSession: Сессия базы данных

    Example:
        @router.get("/")
        async def endpoint(session: AsyncSession = Depends(get_db)):
            ...
    """
    async with db.session() as session:
        yield session


# Инициализация БД (для Alembic миграций)
async def init_db():
    """Инициализирует структуру базы данных (создает таблицы).

    Note:
        Используется для тестов и первоначальной настройки.
        В production следует использовать Alembic.
    """
    if not db.engine:
        await db.connect()

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    log.info("Таблицы базы данных инициализированы")
