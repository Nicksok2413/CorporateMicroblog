import hashlib
from typing import AsyncGenerator, Awaitable, Callable, List, Tuple
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.api.dependencies import pwd_context
from src.core.config import settings
from src.core.database import get_db_session
from src.main import app
from src.models import Base, Media, User


# --- Настройка Тестовой Базы Данных ---
# Создаём движок один раз на сессию
@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Создает асинхронный движок SQLAlchemy для тестовой БД SQLite in-memory.
    Таблицы создаются один раз.
    """
    # Движок создается один раз для всей сессии
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Очищаем перед тестами
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


# Создаем фабрику сессий один раз на сессию
@pytest.fixture(scope="session")
def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Возвращает фабрику сессий SQLAlchemy."""
    return async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )


# Создаем новую сессию для каждой тестовой функции (используем транзакции для изоляции тестов)
@pytest_asyncio.fixture(scope="function")
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Создает сеанс SQLAlchemy с транзакцией, которая откатывается после теста."""
    async with db_session_factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()  # Откатываем транзакцию после теста


# --- Настройка Тестового Клиента FastAPI ---


# Фикстура для переопределения зависимости get_db_session
@pytest_asyncio.fixture(scope="function")
async def override_get_db(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    """Переопределенная зависимость для получения тестовой сессии БД."""
    yield db_session


# Фикстура для создания экземпляра тестового клиента
@pytest_asyncio.fixture(scope="function")
async def client(override_get_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Создает асинхронный тестовый HTTP клиент (httpx.AsyncClient) для FastAPI приложения.
    Переопределяет зависимость get_db_session для использования тестовой БД.
    """
    # Переопределяем зависимость get_db_session
    app.dependency_overrides[get_db_session] = lambda: override_get_db

    # Создаем транспорт для ASGI приложения
    transport = ASGITransport(app=app)

    # Создаем клиент с транспортом
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    # Удаляем переопределение
    del app.dependency_overrides[get_db_session]


# --- Вспомогательные фикстуры ---


# Общая функция для создания пользователя с хешами
async def _create_test_user(
    db_session: AsyncSession,
    name: str,
    api_key: str,
) -> Tuple[User, str]:
    """"""
    key_hash = pwd_context.hash(api_key)
    sha256_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    user = User(name=name, api_key_hash=key_hash, api_key_sha256=sha256_hash)

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, api_key  # Возвращаем объект И исходный ключ


# Фикстура пользователя `Test User`
@pytest_asyncio.fixture(scope="function")
async def test_user_data(db_session: AsyncSession) -> Tuple[User, str]:
    """Создает пользователя `Test User` в БД и возвращает (объект User, исходный api_key)."""
    api_key = f"test_key_{uuid4().hex[:6]}"
    return await _create_test_user(db_session, "Test User", api_key)


# Фикстура пользователя `Test Alice`
@pytest_asyncio.fixture(scope="function")
async def test_user_alice_data(db_session: AsyncSession) -> Tuple[User, str]:
    """Создает пользователя `Test Alice` в БД и возвращает (объект User, исходный api_key)."""
    api_key = f"alice_test_{uuid4().hex[:6]}"
    return await _create_test_user(db_session, "Test Alice", api_key)


# Фикстура пользователя `Test Bob`
@pytest_asyncio.fixture(scope="function")
async def test_user_bob_data(db_session: AsyncSession) -> Tuple[User, str]:
    """Создает пользователя `Test Bob` в БД и возвращает (объект User, исходный api_key)."""
    api_key = f"bob_test_{uuid4().hex[:6]}"
    return await _create_test_user(db_session, "Test Bob", api_key)


# Фикстура для аутентифицированного клиента
@pytest.fixture(scope="function")
def authenticated_client(client: AsyncClient, test_user_data) -> AsyncClient:
    """Возвращает тестовый клиент с установленным api-key тестового пользователя."""
    user_obj, api_key = test_user_data
    client.headers[settings.API_KEY_HEADER] = api_key
    return client


# Фикстура фабрики загрузки медиафайлов
@pytest.fixture(scope="function")
def create_uploaded_media_list(
    authenticated_client: AsyncClient, db_session: AsyncSession
) -> Callable[[int], Awaitable[List[Media]]]:
    """
    Фабрика для создания и загрузки указанного количества медиафайлов.

    Возвращает асинхронную функцию, которая принимает количество медиа (count)
    и возвращает список созданных объектов Media.
    """

    async def _factory(count: int = 1) -> List[Media]:
        """
        Асинхронная фабрика, создающая 'count' медиафайлов.

        Загружает тестовые медиафайлы через API /medias,
        проверяет записи в БД и возвращает объекты Media.
        """
        if count <= 0:
            return []

        media_list = []

        for i in range(count):
            # Создаем "файл" в памяти
            file_content = f"test content {i}".encode()
            filename = f"test_factory_{i}.jpg"
            content_type = "image/jpeg"

            files = {"file": (filename, file_content, content_type)}

            # Используем API для загрузки
            response = await authenticated_client.post("/api/medias", files=files)

            # Проверяем успешность загрузки
            assert response.status_code == status.HTTP_201_CREATED
            json_response = response.json()
            assert json_response["result"] is True
            assert "media_id" in json_response
            media_id = json_response["media_id"]

            # Получаем объект Media из БД
            media: Media | None = await db_session.get(Media, media_id)
            assert media is not None

            # Проверяем, что файл физически создался
            assert (settings.MEDIA_ROOT_PATH / media.file_path).exists()
            assert media.file_path.endswith(filename.split(".")[-1])

            # Проверяем что tweet_id пока NULL
            assert media.tweet_id is None  # Медиа еще не привязано

            media_list.append(media)

        # Возвращаем список созданных объектов
        return media_list

    # Фикстура возвращает саму функцию _factory
    return _factory
