from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.dependencies import get_current_user
from src.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from src.models import User
from src.repositories import UserRepository

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для мока UserRepo
@pytest.fixture
def mock_user_repo() -> MagicMock:
    repo = MagicMock(spec=UserRepository)
    repo.get_by_api_key = AsyncMock()
    return repo


async def test_get_current_user_success(
        mock_db_session: MagicMock,
        mock_user_repo: MagicMock,
        test_user_obj: User
):
    """Тест успешного получения пользователя по api-key."""
    api_key = "valid_key"
    mock_user_repo.get_by_api_key.return_value = test_user_obj

    # Вызываем метод
    user = await get_current_user(db=mock_db_session, user_repo=mock_user_repo, api_key=api_key)

    assert user == test_user_obj
    mock_user_repo.get_by_api_key.assert_awaited_once_with(db=mock_db_session, api_key=api_key)


async def test_get_current_user_no_key(
        mock_db_session: MagicMock,
        mock_user_repo: MagicMock
):
    """Тест вызова без api-key."""
    # Проверяем, что выбрасывается AuthenticationRequiredError
    with pytest.raises(AuthenticationRequiredError) as exc_info:
        await get_current_user(db=mock_db_session, user_repo=mock_user_repo, api_key=None)

    assert "Отсутствует заголовок api-key" in exc_info.value.detail
    mock_user_repo.get_by_api_key.assert_not_awaited()


async def test_get_current_user_invalid_key(
        mock_db_session: MagicMock,
        mock_user_repo: MagicMock
):
    """Тест вызова с ключом, по которому пользователь не найден."""
    api_key = "invalid_key"
    mock_user_repo.get_by_api_key.return_value = None  # Пользователь не найден

    # Проверяем, что выбрасывается PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_current_user(db=mock_db_session, user_repo=mock_user_repo, api_key=api_key)

    assert "Недействительный API ключ" in exc_info.value.detail
    mock_user_repo.get_by_api_key.assert_awaited_once_with(db=mock_db_session, api_key=api_key)
