import hashlib
from unittest.mock import MagicMock, patch

import pytest

from src.api.dependencies import get_current_user
from src.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from src.models.user import User

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# --- Фикстуры ---


# Фикстура для тестового ключа
@pytest.fixture
def plain_api_key() -> str:
    return "my_secret_test_key"


# Фикстура для SHA256 хеша
@pytest.fixture
def api_key_sha256(plain_api_key: str) -> str:
    return hashlib.sha256(plain_api_key.encode("utf-8")).hexdigest()


# --- Тест зависимости для получения текущего пользователя ---


# Мокируем pwd_context.verify внутри каждого теста, где он нужен
@patch("src.api.dependencies.pwd_context.verify")
async def test_get_current_user_success(
    mock_verify: MagicMock,
    mock_db_session: MagicMock,
    mock_user_repo: MagicMock,
    test_user_obj: User,
    plain_api_key: str,
    api_key_sha256: str,
):
    """Тест успешного получения пользователя по хешированному api-key."""
    # Настраиваем моки
    mock_user_repo.get_by_sha256.return_value = test_user_obj
    mock_verify.return_value = True  # Имитируем успешную проверку хеша

    # Вызываем метод
    user = await get_current_user(
        db=mock_db_session, user_repo=mock_user_repo, api_key=plain_api_key
    )

    # Проверки
    assert user == test_user_obj

    # Проверяем, что поиск был по SHA256
    mock_user_repo.get_by_sha256.assert_awaited_once_with(
        db=mock_db_session, sha256_hash=api_key_sha256
    )

    # Проверяем, что pwd_context.verify вызывался правильно
    mock_verify.assert_called_once_with(plain_api_key, test_user_obj.api_key_hash)


@patch("src.api.dependencies.pwd_context.verify")
async def test_get_current_user_verify_fails(
    mock_verify: MagicMock,
    mock_db_session: MagicMock,
    mock_user_repo: MagicMock,
    test_user_obj: User,
    plain_api_key: str,
    api_key_sha256: str,
):
    """Тест случая, когда пользователь найден по SHA256, но проверка хеша не проходит."""
    # Настраиваем моки
    mock_user_repo.get_by_sha256.return_value = test_user_obj
    mock_verify.return_value = False  # Имитируем неуспешную проверку хеша

    # Проверяем, что выбрасывается PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_current_user(
            db=mock_db_session, user_repo=mock_user_repo, api_key=plain_api_key
        )

    assert "Недействительный API ключ" in exc_info.value.detail

    # Проверяем вызовы
    mock_user_repo.get_by_sha256.assert_awaited_once()
    mock_verify.assert_called_once()


async def test_get_current_user_no_key(
    mock_db_session: MagicMock,
    mock_user_repo: MagicMock,
):
    """Тест вызова без api-key."""
    # Проверяем, что выбрасывается AuthenticationRequiredError
    with pytest.raises(AuthenticationRequiredError) as exc_info:
        await get_current_user(
            db=mock_db_session, user_repo=mock_user_repo, api_key=None
        )

    # Проверки
    assert "Отсутствует заголовок api-key" in exc_info.value.detail
    mock_user_repo.get_by_sha256.assert_not_awaited()


async def test_get_current_user_sha256_not_found(
    mock_db_session: MagicMock,
    mock_user_repo: MagicMock,
    plain_api_key: str,
    api_key_sha256: str,
):
    """Тест вызова с ключом, SHA256 которого не найден в БД."""
    # Настраиваем мок репозитория
    mock_user_repo.get_by_sha256.return_value = None  # Пользователь не найден

    # Проверяем, что выбрасывается PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_current_user(
            db=mock_db_session, user_repo=mock_user_repo, api_key=plain_api_key
        )

    # Проверки
    assert "Недействительный API ключ" in exc_info.value.detail
    mock_user_repo.get_by_sha256.assert_awaited_once_with(
        db=mock_db_session, sha256_hash=api_key_sha256
    )


# Мокируем hashlib.sha256().hexdigest()
@patch("hashlib.sha256")
async def test_get_current_user_sha256_exception(
    mock_sha256: MagicMock,  # Мок для hashlib.sha256
    mock_db_session: MagicMock,
    mock_user_repo: MagicMock,
    plain_api_key: str,
):
    """Тест обработки ошибки при вычислении SHA256."""
    # Настраиваем мок sha256, чтобы hexdigest вызывал ошибку
    mock_hash_obj = MagicMock()
    mock_hash_obj.hexdigest.side_effect = Exception("Hashing failed")
    mock_sha256.return_value = mock_hash_obj

    # Проверяем, что выбрасывается PermissionDeniedError с нужным сообщением
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_current_user(
            db=mock_db_session, user_repo=mock_user_repo, api_key=plain_api_key
        )

    # Проверяем сообщение из блока except
    assert "Ошибка обработки ключа" in exc_info.value.detail

    # Проверяем, что хеширование пытались вызвать
    mock_sha256.assert_called_once_with(plain_api_key.encode("utf-8"))
    mock_hash_obj.hexdigest.assert_called_once()
    # Убедимся, что поиск по репозиторию не производился
    mock_user_repo.get_by_sha256.assert_not_awaited()
