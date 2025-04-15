from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Убедимся, что настройки загружены с TESTING=True до импорта приложения
from src.core.config import settings

assert settings.TESTING, "Тесты должны запускаться с TESTING=True"

from src.core.database import Base, get_db_session
from src.main import app
from src.models import Media, User


# --- Фикстура для автоматической очистки временных папок ---
# Используем scope="session", чтобы выполнилось один раз после всех тестов
# autouse=True означает, что фикстура будет использоваться автоматически без явного запроса
@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_dirs(request):
    """Очищает временные директории для медиа и логов после завершения сессии тестов."""
    # Код до yield выполнится перед началом сессии (здесь не нужен)
    yield
    # Код после yield выполнится после завершения сессии
    print("\nОчистка временных директорий после тестов...")

    temp_media_path = Path(gettempdir()) / "temp_media"
    temp_log_path = Path(gettempdir()) / "temp_logs"

    deleted_count = 0
    errors = []

    for temp_path in [temp_media_path, temp_log_path]:
        if temp_path.exists() and temp_path.is_dir():
            try:
                # Используем shutil.rmtree для рекурсивного удаления директории и ее содержимого
                rmtree(temp_path)
                print(f"Успешно удалена директория: {temp_path}")
                deleted_count += 1
            except OSError as exc:
                error_msg = f"Ошибка при удалении директории {temp_path}: {exc}"
                print(error_msg)
                errors.append(error_msg)
        else:
            print(f"Директория для очистки не найдена: {temp_path}")

    if errors:
        print(f"Завершено с ошибками при очистке: {errors}")
    else:
        print(f"Очистка временных директорий завершена ({deleted_count} удалено).")


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
    return async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)


# Создаем новую сессию для каждой тестовой функции (используем транзакции для изоляции тестов)
@pytest_asyncio.fixture(scope="function")
async def db_session(db_session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
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
async def override_get_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
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

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя с уникальным api_key в БД и возвращает его объект."""
    unique_suffix = uuid4().hex[:6]  # Генерируем короткий уникальный суффикс
    user = User(name=f"Test User", api_key=f"test_key_{unique_suffix}")  # Делаем api_key уникальным
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_alice(db_session: AsyncSession) -> User:
    """Создает второго тестового пользователя."""
    user = User(name="Test Alice", api_key="alice_test_key")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_bob(db_session: AsyncSession) -> User:
    """Создает третьего тестового пользователя."""
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


# Фикстура для загрузки медиа
@pytest_asyncio.fixture(scope="function")
async def uploaded_media(
        authenticated_client: AsyncClient,
        db_session: AsyncSession
) -> Media:
    """
    Загружает тестовый медиафайл через API /medias,
    проверяет запись в БД и возвращает объект Media.
    Доступна для всех тестов.
    """
    # Создаем "файл" в памяти
    file_content = b"this is a test image content"
    filename = "test_upload.png"
    content_type = "image/png"

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
    assert media.file_path.endswith(filename.split('.')[-1])  # Проверяем расширение

    # Проверяем что tweet_id пока NULL
    assert media.tweet_id is None  # Медиа еще не привязано

    # Возвращаем созданный и проверенный объект Media
    return media
