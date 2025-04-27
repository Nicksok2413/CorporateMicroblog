from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine.result import ScalarResult

from src.models.user import User
from src.repositories.user import UserRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для создания экземпляра репозитория
@pytest.fixture
def user_repo() -> UserRepository:
    return UserRepository(User)


# --- Тест для get_by_sha256 ---


async def test_get_by_sha256_found(
    user_repo: UserRepository,
    mock_db_session: MagicMock,
    test_user_obj: User,
):
    """Тест get_by_sha256, когда хеш найден."""
    sha256_hash = "a" * 64  # Пример хеша
    test_user_obj.api_key_sha256 = sha256_hash  # Устанавливаем хеш объекту

    # Настраиваем мок результата execute
    mock_result = mock_db_session.execute.return_value
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = test_user_obj
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Вызываем метод
    result = await user_repo.get_by_sha256(db=mock_db_session, sha256_hash=sha256_hash)

    # Проверки
    assert result == test_user_obj
    mock_db_session.execute.assert_awaited_once()
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()


async def test_get_by_sha256_not_found(
    user_repo: UserRepository,
    mock_db_session: MagicMock,
):
    """Тест get_by_sha256, когда хеш не найден."""
    sha256_hash = "notfound" * 8

    # Настраиваем мок результата execute
    mock_result = mock_db_session.execute.return_value
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = None  # Пользователь не найден
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    # Вызываем метод
    result = await user_repo.get_by_sha256(db=mock_db_session, sha256_hash=sha256_hash)

    # Проверки
    assert result is None
    mock_db_session.execute.assert_awaited_once()
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()
