import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db_session
from app.main import app
from app.models import User

# Используем тестовую БД (вероятно, SQLite из settings.TEST_DB_URL)
test_engine = create_async_engine(settings.EFFECTIVE_DATABASE_URL, poolclass=NullPool)  # NullPool для SQLite
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Создает таблицы перед запуском тестов и удаляет после."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield  # Запускаем тесты
    # Удаление таблиц после тестов (опционально, если БД временная)
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Фикстура для предоставления сессии БД в тестах."""
    async with TestingSessionLocal() as session:
        yield session
        # Откат транзакции после каждого теста для изоляции (если нужно)
        # await session.rollback()


@pytest.fixture(scope="session")
def event_loop(request) -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создает event loop для сессии pytest."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Фикстура для создания асинхронного HTTP клиента для тестов API."""

    # Переопределяем зависимость get_db_session для тестов
    def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session  # Используем сессию из фикстуры db_session

    app.dependency_overrides[get_db_session] = override_get_db
    # Используем httpx AsyncClient
    async with AsyncClient(app=app, base_url="http://testserver/api/v1") as test_client:
        yield test_client
    # Очищаем переопределение после теста
    app.dependency_overrides.clear()


# --- Фикстуры для тестовых данных ---
@pytest_asyncio.fixture(scope="function")
async def test_user1(db_session: AsyncSession) -> User:
    user = User(name="Test User 1", api_key="testkey1")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user2(db_session: AsyncSession) -> User:
    user = User(name="Test User 2", api_key="testkey2")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

# Добавьте другие фикстуры для твитов, лайков, подписок по мере необходимости
