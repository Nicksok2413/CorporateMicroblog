from logging import INFO, ERROR
from unittest.mock import MagicMock, patch

import pytest

from src.core import sentry

# Импортируем нужные классы интеграций для проверки
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration


# --- Тесты для initialize_sentry ---


# Используем patch для мокирования sentry_sdk.init и объекта log
@patch("src.core.sentry.sentry_sdk.init", return_value=None)  # Мокируем init
@patch("src.core.sentry.log")  # Мокируем объект log из модуля sentry
def test_initialize_sentry_dsn_provided_production(
    mock_log: MagicMock,
    mock_sentry_init: MagicMock,
    monkeypatch,  # Используем monkeypatch для изменения настроек
):
    """Тест инициализации Sentry в Production режиме при наличии DSN."""
    test_dsn = "https://testkey@test.sentry.io/123"

    # Настройка мока settings через monkeypatch
    # Создаем временный объект настроек с нужными значениями
    mock_settings = MagicMock()
    mock_settings.SENTRY_DSN = test_dsn
    mock_settings.PRODUCTION = True
    mock_settings.TESTING = False
    # Подменяем объект settings внутри модуля sentry
    monkeypatch.setattr(sentry, "settings", mock_settings)

    # Вызываем функцию инициализации
    sentry.initialize_sentry()

    # Проверяем, что log.info и log.success вызывались
    mock_log.info.assert_called()
    mock_log.success.assert_called_with("Sentry SDK успешно инициализирован.")
    # Проверяем, что log.warning не вызывался
    mock_log.warning.assert_not_called()
    # Проверяем, что log.exception не вызывался
    mock_log.exception.assert_not_called()

    # Проверяем, что sentry_sdk.init был вызван один раз
    mock_sentry_init.assert_called_once()

    # Проверяем аргументы вызова sentry_sdk.init
    call_args, call_kwargs = mock_sentry_init.call_args
    assert call_kwargs.get("dsn") == test_dsn
    assert call_kwargs.get("environment") == "production"
    assert call_kwargs.get("traces_sample_rate") == 0.1  # Дефолт для production
    assert call_kwargs.get("profiles_sample_rate") == 0.1  # Дефолт для production

    # Проверяем наличие и типы интеграций
    integrations = call_kwargs.get("integrations", [])
    assert any(isinstance(i, StarletteIntegration) for i in integrations)
    assert any(isinstance(i, FastApiIntegration) for i in integrations)
    assert any(isinstance(i, SqlalchemyIntegration) for i in integrations)
    # Проверяем LoggingIntegration и ее параметры
    logging_integration = next(
        (i for i in integrations if isinstance(i, LoggingIntegration)), None
    )
    assert logging_integration is not None


@patch("src.core.sentry.sentry_sdk.init", return_value=None)
@patch("src.core.sentry.log")
def test_initialize_sentry_dsn_provided_development(
    mock_log: MagicMock, mock_sentry_init: MagicMock, monkeypatch
):
    """Тест инициализации Sentry в Development режиме (не Production, не Testing)."""
    test_dsn = "https://testkey_dev@test.sentry.io/123"

    # Настраиваем мок settings
    mock_settings = MagicMock()
    mock_settings.SENTRY_DSN = test_dsn
    mock_settings.PRODUCTION = False
    mock_settings.TESTING = False  # Важно: DEBUG=True подразумевается
    monkeypatch.setattr(sentry, "settings", mock_settings)

    # Вызываем функцию
    sentry.initialize_sentry()

    # Проверяем логи
    mock_log.info.assert_called()
    mock_log.success.assert_called_with("Sentry SDK успешно инициализирован.")
    mock_log.warning.assert_not_called()
    mock_log.exception.assert_not_called()

    # Проверяем вызов init
    mock_sentry_init.assert_called_once()

    # Проверяем ключевые аргументы для development
    call_args, call_kwargs = mock_sentry_init.call_args
    assert call_kwargs.get("dsn") == test_dsn
    assert call_kwargs.get("environment") == "development"
    assert call_kwargs.get("traces_sample_rate") == 1.0  # 100% для development
    assert call_kwargs.get("profiles_sample_rate") == 1.0  # 100% для development
    assert len(call_kwargs.get("integrations", [])) >= 4  # Проверяем наличие интеграций


@patch("src.core.sentry.sentry_sdk.init", return_value=None)
@patch("src.core.sentry.log")
def test_initialize_sentry_dsn_provided_testing(
    mock_log: MagicMock, mock_sentry_init: MagicMock, monkeypatch
):
    """Тест инициализации Sentry в Testing режиме."""
    test_dsn = "https://testkey_test@test.sentry.io/123"

    # Настраиваем мок settings
    mock_settings = MagicMock()
    mock_settings.SENTRY_DSN = test_dsn
    mock_settings.PRODUCTION = False  # TESTING=True переопределяет PRODUCTION
    mock_settings.TESTING = True
    monkeypatch.setattr(sentry, "settings", mock_settings)

    # Вызываем функцию
    sentry.initialize_sentry()

    # Проверяем логи
    mock_log.info.assert_called()
    mock_log.success.assert_called_with("Sentry SDK успешно инициализирован.")
    mock_log.warning.assert_not_called()
    mock_log.exception.assert_not_called()

    # Проверяем вызов init
    mock_sentry_init.assert_called_once()

    # Проверяем ключевые аргументы для testing
    call_args, call_kwargs = mock_sentry_init.call_args
    assert call_kwargs.get("dsn") == test_dsn
    assert call_kwargs.get("environment") == "testing"
    assert call_kwargs.get("traces_sample_rate") == 0.0  # 0% для testing
    assert call_kwargs.get("profiles_sample_rate") == 0.0  # 0% для testing


@patch("src.core.sentry.sentry_sdk.init", return_value=None)
@patch("src.core.sentry.log")
def test_initialize_sentry_no_dsn(
    mock_log: MagicMock, mock_sentry_init: MagicMock, monkeypatch
):
    """Тест случая, когда SENTRY_DSN не установлен."""

    # Настраиваем мок settings
    mock_settings = MagicMock()
    mock_settings.SENTRY_DSN = None  # DSN не задан
    mock_settings.PRODUCTION = True  # Не важно в этом тесте
    mock_settings.TESTING = False
    monkeypatch.setattr(sentry, "settings", mock_settings)

    # Вызываем функцию
    sentry.initialize_sentry()

    # Проверяем, что sentry_sdk.init НЕ вызывался
    mock_sentry_init.assert_not_called()

    # Проверяем, что было выдано предупреждение
    mock_log.warning.assert_called_once_with(
        "SENTRY_DSN не установлен в .env. Sentry SDK не инициализирован."
    )
    # Проверяем, что другие логи не вызывались
    mock_log.info.assert_not_called()  # Не должно быть лога об инициализации
    mock_log.success.assert_not_called()
    mock_log.exception.assert_not_called()


@patch("src.core.sentry.sentry_sdk.init")  # Не мокируем return_value, имитируем ошибку
@patch("src.core.sentry.log")
def test_initialize_sentry_init_error(
    mock_log: MagicMock, mock_sentry_init: MagicMock, monkeypatch
):
    """Тест обработки ошибки при вызове sentry_sdk.init."""
    test_dsn = "invalid_dsn_format"
    init_error = ValueError("Sentry init failed")

    # Настраиваем мок settings
    mock_settings = MagicMock()
    mock_settings.SENTRY_DSN = test_dsn
    mock_settings.PRODUCTION = False
    mock_settings.TESTING = False
    monkeypatch.setattr(sentry, "settings", mock_settings)

    # Настраиваем мок init на выброс исключения
    mock_sentry_init.side_effect = init_error

    # Вызываем функцию
    sentry.initialize_sentry()

    # Проверяем, что sentry_sdk.init был вызван
    mock_sentry_init.assert_called_once()

    # Проверяем, что log.exception был вызван с правильным исключением
    mock_log.exception.assert_called_once_with(
        f"Ошибка инициализации Sentry SDK: {init_error}"
    )
    # Проверяем, что другие логи не вызывались или вызывались до ошибки
    mock_log.info.assert_called()  # Лог о попытке инициализации должен быть
    mock_log.success.assert_not_called()  # Успеха не было
    mock_log.warning.assert_not_called()
