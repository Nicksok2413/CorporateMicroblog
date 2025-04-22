import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings
from src.core.database import Database, get_db_session


# --- Фикстуры ---


# Фикстура для мока AsyncEngine
@pytest.fixture
def mock_engine() -> MagicMock:
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


# Фикстура для мока фабрики сессий
@pytest.fixture
def mock_session_factory(mock_db_session: MagicMock) -> MagicMock:
    """Мок для async_sessionmaker, возвращающий мок сессии."""
    factory = MagicMock(spec=async_sessionmaker)
    # При вызове фабрики она возвращает наш мок сессии
    factory.return_value = mock_db_session
    # Чтобы фабрика была вызываемой (как в db.session_factory())
    factory.__call__ = MagicMock(return_value=mock_db_session)
    return factory


# --- Тесты для класса Database ---


def test_database_initialization():
    """Тест инициализации класса Database."""
    db = Database()
    assert db.engine is None
    assert db.session_factory is None


# Используем patch для мокирования функций на уровне модуля
@pytest.mark.asyncio
@patch("src.core.database.create_async_engine")
@patch("src.core.database.async_sessionmaker")
@patch(
    "src.core.database.Database._verify_connection", new_callable=AsyncMock
)  # Мок верификации
async def test_database_connect_success(
    mock_verify: AsyncMock,
    mock_sessionmaker: MagicMock,
    mock_create_engine: MagicMock,
    mock_engine: MagicMock,
    mock_session_factory: MagicMock,
):
    """Тест успешного подключения к БД."""
    # Настраиваем моки
    mock_create_engine.return_value = mock_engine
    mock_sessionmaker.return_value = mock_session_factory

    db = Database()
    await db.connect(extra_arg="test")  # Проверяем передачу доп. аргументов

    # Проверяем вызовы
    mock_create_engine.assert_called_once_with(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=3600,
        extra_arg="test",  # Проверяем доп. аргумент
    )
    mock_sessionmaker.assert_called_once_with(
        bind=mock_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    mock_verify.assert_awaited_once()  # Проверяем, что верификация вызывалась

    # Проверяем установленные атрибуты
    assert db.engine == mock_engine
    assert db.session_factory == mock_session_factory


@pytest.mark.asyncio
@patch("src.core.database.create_async_engine")
@patch("src.core.database.async_sessionmaker")
@patch("src.core.database.Database._verify_connection", new_callable=AsyncMock)
async def test_database_connect_verify_failure(
    mock_verify: AsyncMock,
    mock_sessionmaker: MagicMock,
    mock_create_engine: MagicMock,
):
    """Тест ошибки при верификации подключения."""
    # Настраиваем моки
    mock_verify.side_effect = RuntimeError(
        "Verification failed"
    )  # Ошибка при верификации

    db = Database()
    with pytest.raises(RuntimeError, match="Verification failed"):
        await db.connect()

    # Проверяем, что верификация вызывалась
    mock_verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_disconnect_success(mock_engine: MagicMock):
    """Тест успешного отключения от БД."""
    db = Database()
    # Имитируем подключенное состояние
    db.engine = mock_engine
    db.session_factory = MagicMock()  # Не важно какой, главное не None

    await db.disconnect()

    # Проверяем вызов dispose
    mock_engine.dispose.assert_awaited_once()
    # Проверяем, что атрибуты сброшены
    assert db.engine is None
    assert db.session_factory is None


@pytest.mark.asyncio
async def test_database_disconnect_no_engine():
    """Тест отключения, когда движок уже None."""
    db = Database()
    # Ничего не должно произойти, не должно быть ошибки
    await db.disconnect()
    assert db.engine is None
    assert db.session_factory is None


@pytest.mark.asyncio
@patch("src.core.database.text")  # Мокируем text, чтобы не зависеть от sqlalchemy
async def test_database_verify_connection_success(
    mock_sa_text: MagicMock,
    mock_session_factory: MagicMock,
    mock_db_session: MagicMock,
):
    """Тест успешной верификации соединения."""
    # Настраиваем моки
    mock_sa_text.return_value = "SELECT 1 SQL"  # Возвращаем строку для execute

    db = Database()
    db.session_factory = mock_session_factory  # Устанавливаем мок фабрики

    await db._verify_connection()

    # Проверяем, что сессия была создана и использована
    mock_session_factory.assert_called_once()
    mock_db_session.execute.assert_awaited_once_with(
        "SELECT 1 SQL"
    )  # Проверяем вызов execute


@pytest.mark.asyncio
async def test_database_verify_connection_db_error(
    mock_session_factory: MagicMock,
    mock_db_session: MagicMock,
):
    """Тест ошибки БД при верификации соединения."""
    # Настраиваем мок execute на выброс ошибки
    db_error = OperationalError("Connection failed", {}, None)
    mock_db_session.execute.side_effect = db_error

    db = Database()
    db.session_factory = mock_session_factory

    with pytest.raises(
        RuntimeError, match="Не удалось проверить подключение к БД."
    ) as exc_info:
        await db._verify_connection()

    # Убедимся, что исходная ошибка сохранена в __cause__ или __context__
    assert exc_info.value.__cause__ is db_error

    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_verify_connection_factory_not_set():
    """Тест верификации, когда фабрика сессий не установлена."""
    db = Database()
    with pytest.raises(RuntimeError, match="Фабрика сессий не инициализирована."):
        await db._verify_connection()


@pytest.mark.asyncio
async def test_database_session_success(
    mock_session_factory: MagicMock,
    mock_db_session: MagicMock,
):
    """Тест успешного получения и использования сессии через контекстный менеджер."""
    db = Database()
    db.session_factory = mock_session_factory

    async with db.session() as session:
        assert session == mock_db_session
        # Проверяем, что rollback и close еще не вызывались
        mock_db_session.rollback.assert_not_awaited()
        mock_db_session.close.assert_not_awaited()

    # Проверяем, что close был вызван после выхода из блока
    mock_db_session.close.assert_awaited_once()
    # Проверяем, что rollback не вызывался (т.к. не было ошибки)
    mock_db_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_session_exception_and_rollback(
    mock_session_factory: MagicMock,
    mock_db_session: MagicMock,
):
    """Тест отката транзакции при ошибке внутри контекстного менеджера сессии."""
    db = Database()
    db.session_factory = mock_session_factory
    test_exception = ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        async with db.session():
            # Имитируем ошибку внутри блока
            raise test_exception

    # Проверяем, что rollback был вызван
    mock_db_session.rollback.assert_awaited_once()
    # Проверяем, что close был вызван (в блоке finally)
    mock_db_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_session_factory_not_set():
    """Тест получения сессии, когда фабрика не установлена."""
    db = Database()
    with pytest.raises(RuntimeError, match="База данных не инициализирована."):
        async with db.session():
            pass  # Не дойдет сюда


# --- Тесты для зависимости get_db_session ---


@pytest.mark.asyncio
@patch(
    "src.core.database.db", new_callable=MagicMock
)  # Мокируем глобальный экземпляр db
async def test_get_db_session_dependency_success(
    mock_global_db: MagicMock,
    mock_db_session: MagicMock,
):
    """Тест успешного получения сессии через зависимость FastAPI."""
    # Настраиваем мок контекстного менеджера db.session()
    mock_global_db.session.return_value = (
        mock_db_session  # Контекстный менеджер вернет мок сессии
    )

    # Итерируемся по генератору зависимости
    yielded_session = None
    async for session in get_db_session():
        yielded_session = session

    # Проверяем, что был вызван контекстный менеджер глобального объекта db
    mock_global_db.session.assert_called_once()
    # Проверяем, что контекстный менеджер был корректно открыт и закрыт
    mock_db_session.__aenter__.assert_awaited_once()
    mock_db_session.__aexit__.assert_awaited_once()
    # Проверяем, что зависимость вернула правильную сессию
    assert yielded_session == mock_db_session
