"""Настройка конфигурации логирования для приложения с использованием Loguru."""

import json
import sys
from pathlib import Path

from loguru import logger


def serialize(record):
    """
    Кастомная сериализация для записи логов в формате JSON.

    Args:
        record: Запись лога Loguru.

    Returns:
        str: Сериализованная в JSON строка лога.
    """
    subset = {
        "timestamp": record["time"].isoformat(),
        "message": record["message"],
        "level": record["level"].name,
        "name": record["name"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    # Добавляем extra данные, если они есть
    if record["extra"]:
        subset["extra"] = record["extra"]
    # Добавляем информацию об исключении, если она есть
    if record["exception"]:
        exception_type, exception_value, traceback = record["exception"]
        subset["exception"] = {
            "type": str(exception_type),
            "value": str(exception_value),
            # Трейсбек не добавляем в JSON по умолчанию, т.к. может быть большим
        }
    return json.dumps(subset, ensure_ascii=False)


def development_formatter(record):
    """
    Форматтер для цветного консольного вывода в режиме разработки.

    Args:
        record: Запись лога Loguru.

    Returns:
        str: Отформатированная строка лога для консоли.
    """
    # Базовый формат
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    # Добавляем информацию об исключении, если есть
    if record["exception"]:
        log_format += "\n<red>{exception}</red>"  # Loguru автоматически форматирует exception

    return log_format


def configure_logging():
    """
    Настраивает Loguru для приложения.

    Удаляет стандартные обработчики и добавляет новые:
    - Цветной вывод в stderr для разработки.
    - JSON вывод в stderr для production.
    - Опциональный вывод в файл с ротацией для production.
    - Специальная обработка логов SQLAlchemy в режиме DEBUG.
    """
    from app.core.config import settings

    # Удаляем стандартный обработчик, чтобы избежать дублирования
    logger.remove()

    # Определяем форматтер в зависимости от режима
    formatter_func = development_formatter if settings.DEBUG else serialize

    # Основной обработчик для вывода в stderr
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=formatter_func,
        # Фильтруем стандартные логи доступа uvicorn по имени логгера
        filter=lambda record: record["name"] != "uvicorn.access",
        colorize=settings.DEBUG,  # Цветной вывод только в DEBUG
        backtrace=settings.DEBUG,  # Подробный трейсбек только в DEBUG
        diagnose=settings.DEBUG  # Диагностика переменных только в DEBUG
    )

    # Файловый вывод (если указан LOG_FILE или включен PRODUCTION)
    log_file_path = settings.LOG_FILE
    if not log_file_path and settings.PRODUCTION:
        # По умолчанию пишем в logs/app.log в production, если LOG_FILE не задан явно
        log_file_path = Path("logs") / "app.log"
        # Создаем директорию, если нужно (на случай, если model_post_init в config не сработал)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

    if log_file_path:
        logger.info(f"Логирование в файл включено: {log_file_path}")
        logger.add(
            log_file_path,
            rotation="100 MB",  # Ротация при достижении 100 MB
            retention="30 days",  # Хранить логи за последние 30 дней
            compression="zip",  # Сжимать старые логи
            level=settings.LOG_LEVEL,  # Уровень для записи в файл
            format=serialize,  # Всегда JSON в файле
            enqueue=True,  # Асинхронная запись для производительности
            # Не фильтруем uvicorn.access для файла, т.к. там он может быть полезен
            backtrace=True,  # Пишем трейсбеки в файл всегда
            diagnose=False  # Диагностику в файл не пишем
        )

    # Настройка логирования SQLAlchemy (только в DEBUG)
    if settings.DEBUG:
        logger.enable("sqlalchemy.engine")  # Включаем логгер SQLAlchemy
    else:
        logger.disable("sqlalchemy.engine")  # Отключаем SQL логи в production

    logger.info(f"Loguru сконфигурирован. Уровень: {settings.LOG_LEVEL}. Режим DEBUG: {settings.DEBUG}")


# Инициализация логирования при импорте модуля
# Комментируем строку при тестах, иначе будет ошибка:
# ImportError: cannot import name 'settings' from partially initialized module 'app.core.config' (most likely due to a circular import)
# TODO: Подумать как решить эту проблему
configure_logging()

# Экспортируем настроенный логгер для использования в других модулях
log = logger
