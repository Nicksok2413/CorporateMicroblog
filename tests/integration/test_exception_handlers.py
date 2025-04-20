from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from src.api.dependencies import get_user_service
from src.main import app
from src.services.user_service import UserService


@pytest.mark.asyncio
async def test_generic_exception_handler(authenticated_client: AsyncClient):
    """
    Тест проверяет работу generic_exception_handler,
    имитируя непредвиденную ошибку в сервисе.
    """
    error_message = "Something went terribly wrong internally!"

    # Запоминаем оригинальную зависимость
    original_get_user_service = app.dependency_overrides.get(get_user_service)

    # Создаем мок сервиса UserService
    mock_service_instance = MagicMock(spec=UserService)

    # Заставляем метод get_user_profile выбрасывать стандартную ошибку
    mock_service_instance.get_user_profile = AsyncMock(
        side_effect=RuntimeError(error_message)
    )

    # Переопределяем зависимость get_user_service, чтобы она возвращала наш мок
    app.dependency_overrides[get_user_service] = lambda: mock_service_instance


    # Ожидаем, что вызов клиента выбросит именно RuntimeError
    with pytest.raises(RuntimeError, match=error_message):
        try:
            await authenticated_client.get("/api/users/me")
        finally:
            # Восстанавливаем зависимости в любом случае
            if original_get_user_service:
                app.dependency_overrides[get_user_service] = original_get_user_service
            else:
                if get_user_service in app.dependency_overrides:
                    del app.dependency_overrides[get_user_service]

        # Убедимся, что мокированный метод был вызван
        mock_service_instance.get_user_profile.assert_awaited_once()
