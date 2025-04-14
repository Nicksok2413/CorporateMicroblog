import asyncio
from typing import AsyncGenerator, Generator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Импортируем Base и все модели для create_all
from src.models.base import Base
import src.models  # noqa F401: Импорт нужен для регистрации моделей в Base.metadata

# Импортируем приложение FastAPI и настройки
from src.main import app as fastapi_app
from src.core.config import settings
from src.core.database import Base, get_db_session, db as global_db_manager  # Импортируем менеджер БД


# --- Базовые настройки для асинхронных тестов ---

# Фикстура event_loop нужна для сессионных асинхронных фикстур
@pytest.fixture(scope="session")
def event_loop(request) -> Generator:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- Фикстуры для работы с тестовой базой данных ---

@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Создает и очищает тестовую базу данных один раз за сессию.
    Управляет подключением через глобальный менеджер db.
    """
    if not settings.TESTING:
        raise RuntimeError("Тесты должны запускаться с TESTING=True в настройках!")

    # Используем URL из настроек (который должен указывать на тестовую БД)
    db_url = settings.DATABASE_URL
    print(f"\n--- Настройка тестовой БД ({db_url}) ---")

    # Создаем engine специально для тестов (без пула)
    # Важно: используем NullPool для тестов, чтобы избежать проблем с event loop
    test_engine = create_async_engine(db_url, poolclass=NullPool)

    # Создаем все таблицы
    async with test_engine.begin() as conn:
        print("Удаление старых таблиц...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Создание новых таблиц...")
        await conn.run_sync(Base.metadata.create_all)
        print("Таблицы созданы.")

    # Устанавливаем тестовый engine и session_factory в глобальный менеджер db
    # Это нужно, чтобы зависимость get_db_session внутри приложения работала с тестовой БД
    global_db_manager.engine = test_engine
    global_db_manager.session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    print("--- Тестовая БД настроена ---")

    yield  # Запуск тестов

    print("\n--- Очистка тестовой БД ---")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    # Восстанавливаем None, чтобы не влиять на другие возможные использования менеджера
    global_db_manager.engine = None
    global_db_manager.session_factory = None
    print("--- Тестовая БД очищена ---")


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Предоставляет чистую сессию БД для каждого теста с автоматическим откатом.
    Использует фабрику сессий, настроенную в setup_test_database.
    """
    if not global_db_manager.session_factory:
        pytest.fail("Фабрика сессий для тестов не инициализирована!")

    async with global_db_manager.session_factory() as session:
        # Начинаем транзакцию (или точку сохранения)
        # В SQLite begin_nested работает как обычный begin, что подходит
        await session.begin_nested()
        yield session
        # Откатываем транзакцию после теста, чтобы изолировать данные
        await session.rollback()


# --- Фикстуры для работы с FastAPI приложением и HTTP клиентом ---

@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Экземпляр FastAPI приложения для тестов."""

    # Приложение уже импортировано как fastapi_app
    # Убедимся, что зависимости будут использовать тестовую БД
    # Переопределяем зависимость get_db_session для тестов, чтобы она использовала
    # ту же session_factory, что и фикстура db_session.
    # Это гарантирует, что и тесты, и приложение работают с одной тестовой БД.
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        if not global_db_manager.session_factory:
            raise RuntimeError("Тестовая фабрика сессий не готова для override_get_db_session")
        async with global_db_manager.session_factory() as session:
            # Важно: не начинаем здесь транзакцию, т.к. каждый запрос должен
            # быть в своей мини-транзакции, управляемой сервисами или контекстом сессии.
            # Фикстура db_session используется для подготовки/проверки данных вне запросов.
            yield session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    return fastapi_app


@pytest.fixture(scope="function")
async def async_client(test_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Асинхронный HTTP клиент для отправки запросов к тестовому приложению."""
    async with httpx.AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client


# --- Фикстуры для тестовых данных ---
# Используем scope="function", чтобы данные создавались заново для каждого теста,
# гарантируя изоляцию, особенно если тесты модифицируют данные.

@pytest.fixture(scope="function")
async def test_user_nick(db_session: AsyncSession) -> src.models.User:
    """Создает тестового пользователя Nick (ID=1)"""
    user = src.models.User(id=1, name="Nick", api_key="test")
    db_session.add(user)
    await db_session.commit()  # Коммит нужен, чтобы ID был доступен
    await db_session.refresh(user)  # Обновляем объект из БД
    return user


@pytest.fixture(scope="function")
async def test_user_alice(db_session: AsyncSession) -> src.models.User:
    """Создает тестового пользователя Alice (ID=2)"""
    user = src.models.User(id=2, name="Alice", api_key="alice_key")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_user_bob(db_session: AsyncSession) -> src.models.User:
    """Создает тестового пользователя Bob (ID=3)"""
    user = src.models.User(id=3, name="Bob", api_key="bob_key")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_media(db_session: AsyncSession) -> src.models.Media:
    """Создает тестовый медиафайл"""
    media = src.models.Media(id=1, file_path="test_image.jpg")
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)
    return media


@pytest.fixture(scope="function")
async def nick_headers(test_user_nick: src.models.User) -> dict:
    """Заголовки для аутентификации Nick"""
    return {"api-key": test_user_nick.api_key}


@pytest.fixture(scope="function")
async def alice_headers(test_user_alice: src.models.User) -> dict:
    """Заголовки для аутентификации Alice"""
    return {"api-key": test_user_alice.api_key}


@pytest.fixture(scope="function")
async def bob_headers(test_user_bob: src.models.User) -> dict:
    """Заголовки для аутентификации Bob"""
    return {"api-key": test_user_bob.api_key}


@pytest.fixture(scope="function")
async def tweet_from_alice(db_session: AsyncSession, test_user_alice: src.models.User) -> src.models.Tweet:
    """Создает твит от Alice"""
    tweet = src.models.Tweet(content="Alice's tweet content", author_id=test_user_alice.id)
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    return tweet
