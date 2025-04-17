from pathlib import Path
from tempfile import gettempdir

# Важно импортировать Settings до того, как monkeypatch сработает глобально
from src.core.config import Settings


def test_settings_testing_mode(monkeypatch):
    # Текущие фикстуры уже используют TESTING=True, проверим это
    settings = Settings()  # Пересоздаем с учетом окружения
    assert settings.TESTING is True
    assert settings.PRODUCTION is False
    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:///:memory:")
    assert settings.MEDIA_ROOT_PATH == Path(gettempdir()) / "temp_media"
    assert settings.LOG_ROOT_PATH == Path(gettempdir()) / "temp_logs"
    assert settings.LOG_FILE_PATH is None  # Не production


def test_settings_production_mode(monkeypatch):
    # Мокируем переменные окружения для имитации Production
    monkeypatch.setenv("TESTING", "False")
    monkeypatch.setenv("DEBUG", "False")
    # Убедимся, что переменные для DB заданы (иначе Settings упадет)
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    # Пересоздаем объект Settings с новым окружением
    settings = Settings()

    assert settings.TESTING is False
    assert settings.DEBUG is False
    assert settings.PRODUCTION is True
    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")
    assert settings.MEDIA_ROOT_PATH == Path("/media")
    assert settings.LOG_ROOT_PATH == Path("/logs")
    assert settings.LOG_FILE_PATH == Path("/logs/app.log")


def test_settings_debug_mode(monkeypatch):
    monkeypatch.setenv("TESTING", "False")
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    settings = Settings()
    assert settings.TESTING is False
    assert settings.DEBUG is True
    assert settings.PRODUCTION is False
    assert settings.LOG_FILE_PATH is None  # Не production
