from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine.result import ScalarResult

from src.models import User
from src.repositories import UserRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio

# --- Фикстуры ---
@pytest.fixture
def user_repo() -> UserRepository:
    return UserRepository(User)  # Передаем модель


# --- Тест для get_by_api_key ---

async def test_get_by_api_key_found(
        user_repo: UserRepository,
        mock_db_session: MagicMock,
        test_user_obj: User  # Фикстура из unit/conftest.py
):
    api_key = "found_key"
    test_user_obj.api_key = api_key

    mock_result = mock_db_session.execute.return_value
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = test_user_obj
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    result = await user_repo.get_by_api_key(db=mock_db_session, api_key=api_key)

    assert result == test_user_obj
    mock_db_session.execute.assert_awaited_once()
    # Можно добавить проверку самого statement, если нужно
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()


async def test_get_by_api_key_not_found(
        user_repo: UserRepository,
        mock_db_session: MagicMock
):
    api_key = "not_found_key"

    mock_result = mock_db_session.execute.return_value
    mock_scalars = MagicMock(spec=ScalarResult)
    mock_scalars.first.return_value = None  # Пользователь не найден
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    result = await user_repo.get_by_api_key(db=mock_db_session, api_key=api_key)

    assert result is None
    mock_db_session.execute.assert_awaited_once()
    mock_result.scalars.assert_called_once()
    mock_scalars.first.assert_called_once()
