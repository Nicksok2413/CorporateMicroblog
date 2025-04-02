"""Конфигурация и фикстуры для Pytest."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio  # Импортируем для использования асинхронных фикстур
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)

# Импортируем ключевые компоненты приложения
from app.core.config import settings
from app.core.database import Database, get_db_session  # Импортируем класс и зависимость
from app.main import app as main_app  # Импортируем основной экземпляр FastAPI
from app.models import Base, Tweet, User  # Импортируем Base для работы с метаданными

# --- Базовая настройка ---
# Указываем pytest использовать asyncio для всех тестов
# (Если не указано в pytest.ini asyncio_mode = auto)
pytestmark = pytest.mark.asyncio


# --- Фикстуры для работы с БД ---

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создает event loop для сессии pytest."""
    # Стандартная фикстура для pytest-asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Создает асинхронный движок для тестовой БД (SQLite)."""
    # Убедимся, что мы в режиме тестирования
    if not settings.TESTING:
        pytest.fail("Тесты должны запускаться с TESTING=True в настройках.")
    if not settings.EFFECTIVE_DATABASE_URL.startswith("sqlite"):
        pytest.fail("Тесты ожидают SQLite в качестве тестовой БД (TEST_DB_URL).")

    engine = create_async_engine(settings.EFFECTIVE_DATABASE_URL, echo=False)  # echo=False для тестов
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Удаляем старые таблицы
        await conn.run_sync(Base.metadata.create_all)  # Создаем новые
    print(f"\nТестовая БД инициализирована: {settings.EFFECTIVE_DATABASE_URL}")
    yield engine
    # Закрываем движок после завершения всех тестов сессии
    await engine.dispose()
    print(f"\nТестовая БД закрыта: {settings.EFFECTIVE_DATABASE_URL}")
    # Можно удалить файл БД, если он создавался
    # import os
    # db_path = settings.EFFECTIVE_DATABASE_URL.split("///")[-1]
    # if os.path.exists(db_path):
    #     os.remove(db_path)


@pytest_asyncio.fixture(scope="function")  # Сессия на каждую функцию для изоляции
async def db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет асинхронную сессию для тестовой БД."""
    session_factory = async_sessionmaker(
        bind=test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        # Начинаем транзакцию для теста
        await session.begin()
        try:
            yield session
        finally:
            # Откатываем транзакцию после каждого теста для изоляции
            await session.rollback()


# --- Фикстуры для FastAPI приложения и HTTP клиента ---

@pytest.fixture(scope="session")  # Достаточно одной сессии для приложения
def test_app(db_session: AsyncSession) -> FastAPI:  # Зависит от db_session для переопределения
    """Создает экземпляр FastAPI приложения для тестов с переопределенной зависимостью БД."""

    # Функция для переопределения зависимости get_db_session
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        # Эта функция будет использоваться вместо реальной get_db_session
        # Мы не можем использовать db_session напрямую здесь, так как ее scope='function'
        # Поэтому создаем новую сессию из того же движка для каждого запроса к API
        engine = db_session.bind  # Получаем движок из сессии фикстуры
        if not engine:
            pytest.fail("Не удалось получить движок из тестовой сессии БД.")

        session_factory_override = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory_override() as session:
            # Не начинаем транзакцию здесь, пусть управляется внутри эндпоинта/репозитория
            yield session

    # Применяем переопределение зависимости
    main_app.dependency_overrides[get_db_session] = override_get_db_session
    print("\nЗависимость get_db_session переопределена для тестов.")
    return main_app


@pytest_asyncio.fixture(scope="function")  # Клиент на каждую функцию
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Предоставляет асинхронный HTTP клиент для тестирования API."""
    # Используем ASGITransport для прямого взаимодействия с ASGI приложением без сети
    transport = ASGITransport(app=test_app)  # type: ignore
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\nAsyncClient создан.")
        yield client
    print("\nAsyncClient закрыт.")


# --- Фикстуры с тестовыми данными (Примеры) ---

@pytest_asyncio.fixture(scope="function")  # Данные на каждую функцию для изоляции
async def test_user_alice(db_session: AsyncSession) -> User:
    """Создает тестового пользователя Alice в БД."""
    user_data = {"name": "TestAlice", "api_key": "test_alice_key"}
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()  # Коммитим, чтобы пользователь был доступен для API запросов
    await db_session.refresh(user)
    print(f"\nСоздан тестовый пользователь: {user.name} (ID: {user.id})")
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_bob(db_session: AsyncSession) -> User:
    """Создает тестового пользователя Bob в БД."""
    user_data = {"name": "TestBob", "api_key": "test_bob_key"}
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    print(f"\nСоздан тестовый пользователь: {user.name} (ID: {user.id})")
    return user


@pytest_asyncio.fixture(scope="function")
async def test_tweet_by_alice(db_session: AsyncSession, test_user_alice: User) -> Tweet:
    """Создает тестовый твит от пользователя Alice."""
    tweet_data = {"content": "Test tweet content by Alice", "author_id": test_user_alice.id}
    tweet = Tweet(**tweet_data)
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    print(f"\nСоздан тестовый твит: ID {tweet.id} от {test_user_alice.name}")
    return tweet
