"""Настройка подключения к базе данных с использованием SQLAlchemy.

Содержит:
- Настройку асинхронного движка БД
- Фабрику сессий
- Утилиты для управления подключением
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import log
from app.models.base import Base


class Database:
    """
    Менеджер подключений к базе данных.

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
        """
        Устанавливает подключение к базе данных.

        Использует `EFFECTIVE_DATABASE_URL` из настроек.

        Args:
            **kwargs: Дополнительные параметры для create_async_engine.

        Raises:
            RuntimeError: При неудачной проверке подключения.
        """
        db_url = settings.EFFECTIVE_DATABASE_URL
        log.info(f"Подключение к базе данных: {'*' * 5}{db_url[-20:]}")  # Логируем URL (частично скрытый)

        self.engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,  # Включаем логирование SQL запросов в режиме DEBUG
            future=True,   # Включение нового стиля использования SQLAlchemy
            pool_pre_ping=True,  # Проверять соединение перед использованием
            pool_recycle=3600,  # Переподключение каждый час
            **kwargs
        )

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,  # Управляем транзакциями явно
            autoflush=False  # Управляем flush явно
        )

        await self._verify_connection()
        log.success(f"Подключение к базе данных установлено.")

    async def disconnect(self):
        """Корректное закрытие подключения к базе данных."""
        if self.engine:
            log.info("Закрытие подключения к базе данных...")
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            log.info("Подключение к базе данных успешно закрыто.")

    async def _verify_connection(self):
        """
        Проверяет работоспособность подключения к базе данных.

        Raises:
            RuntimeError: Если проверка подключения не удалась.
        """
        if not self.session_factory:
            raise RuntimeError("Фабрика сессий не инициализирована.")
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            log.debug("Проверка подключения к БД прошла успешно.")
        except Exception as exc:
            log.critical(f"Ошибка подключения к базе данных: {exc}", exc_info=True)
            raise RuntimeError("Не удалось проверить подключение к БД.") from exc

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Асинхронный контекстный менеджер для работы с сессиями БД.

        Yields:
            AsyncSession: Экземпляр сессии БД.

        Raises:
            RuntimeError: При вызове до инициализации подключения (`db.connect`).
        """
        if not self.session_factory:
            raise RuntimeError(
                "База данных не инициализирована. Вызовите `await db.connect()` перед использованием сессий.")

        session: AsyncSession = self.session_factory()
        try:
            yield session
            # Коммит не делаем здесь, должен управляться в репозитории/сервисе
        except Exception as exc:
            log.error(f"Ошибка во время сессии БД, выполняется откат: {exc}",
                      exc_info=settings.DEBUG)  # Трейсбек только в DEBUG
            await session.rollback()
            raise  # Перевыбрасываем исключение для обработки выше
        finally:
            await session.close()  # Закрываем сессию


# Глобальный экземпляр менеджера БД
db = Database()


# Dependency для FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость FastAPI для получения асинхронной сессии базы данных.

    Yields:
        AsyncSession: Сессия базы данных, управляемая через `db.session()`.
    """
    async with db.session() as session:
        yield session


# Инициализация БД (в основном для тестов или dev окружения)
async def init_db():
    """
    Инициализирует структуру базы данных (создает таблицы).

    Note:
        Используется в основном для тестов и первоначальной настройки.
        В production для управления схемой БД следует использовать Alembic.
    """
    if not db.engine:
        # Обычно connect вызывается через lifespan, но для прямого вызова добавим
        await db.connect()
        log.warning("Вызван init_db() без активного движка, выполнено подключение.")

    if settings.TESTING and settings.EFFECTIVE_DATABASE_URL.startswith("sqlite"):
        log.info("Используется SQLite, создание таблиц...")
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        log.success("Таблицы для тестовой БД (SQLite) созданы.")
    elif not settings.PRODUCTION:
        log.warning("init_db() не рекомендуется использовать вне тестового режима с SQLite. Используйте Alembic.")
    else:
        log.error("Попытка вызова init_db() в production режиме! Используйте Alembic.")
