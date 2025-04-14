import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Убедимся, что настройки загружены с TESTING=True до импорта приложения
from src.core.config import settings

assert settings.TESTING, "Тесты должны запускаться с TESTING=True"

from src.core.database import Base, get_db_session  # Импортируем зависимость БД
from src.main import app  # Импортируем наше FastAPI приложение
from src.models import User  # Импортируем модель User для фикстуры


# --- Настройка Event Loop ---
# Используем один event loop для всех тестов в сессии
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- Настройка Тестовой Базы Данных ---
# Создаем движок один раз на сессию
@pytest.fixture(scope="session")
async def db_engine():
    """Создает асинхронный движок SQLAlchemy для тестовой БД SQLite."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Очищаем перед тестами
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


# Создаем фабрику сессий один раз на сессию
@pytest.fixture(scope="session")
def db_session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    """Возвращает фабрику сессий SQLAlchemy."""
    return async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)


# Создаем новую сессию для каждой тестовой функции (используем транзакции для изоляции тестов)
@pytest_asyncio.fixture(scope="function")
async def db_session(db_session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """Yields a SQLAlchemy session with a transaction that is rolled back after the test."""
    async with db_session_factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()  # Откатываем транзакцию после теста


# --- Настройка Тестового Клиента FastAPI ---

# Фикстура для переопределения зависимости get_db_session
@pytest_asyncio.fixture(scope="function")
async def override_get_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Переопределенная зависимость для получения тестовой сессии БД."""
    yield db_session


# Фикстура для создания экземпляра тестового клиента
@pytest.fixture(scope="function")
async def client(override_get_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Создает асинхронный тестовый HTTP клиент (httpx.AsyncClient) для FastAPI приложения.
    Переопределяет зависимость get_db_session для использования тестовой БД.
    """
    # Переопределяем зависимость get_db_session на время работы клиента
    app.dependency_overrides[get_db_session] = lambda: override_get_db

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client

    # Удаляем переопределение после теста (хотя для function scope это не так критично)
    del app.dependency_overrides[get_db_session]


# --- Вспомогательные фикстуры ---

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя в БД и возвращает его объект."""
    user = User(name="Test User", api_key="test_key")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_bob(db_session: AsyncSession) -> User:
    """Создает второго тестового пользователя."""
    user = User(name="Test Bob", api_key="bob_test_key")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# Фикстура для аутентифицированного клиента
@pytest.fixture(scope="function")
def authenticated_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Возвращает тестовый клиент с установленным заголовком api-key тестового пользователя."""
    client.headers[settings.API_KEY_HEADER] = test_user.api_key
    return client
