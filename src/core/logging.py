"""Настройка конфигурации логирования для приложения с использованием Loguru."""

import sys

from loguru import logger

from src.core.config import settings


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
        "<level>{level: <5}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>\n"
    )
    # Добавляем информацию об исключении, если есть
    if record["exception"]:
        log_format += "\n<red>{exception}</red>"  # Loguru автоматически форматирует exception

    return log_format


def configure_logging():
    """
    Настраивает Loguru для приложения.

    Удаляет стандартные обработчики и добавляет новые:
    - Цветной вывод в stderr для DEBUG=True.
    - JSON вывод в stderr для DEBUG=False.
    - Вывод в файл с ротацией для PRODUCTION=True.
    - Специальная обработка логов SQLAlchemy в DEBUG-режиме.
    """
    # Удаляем стандартный обработчик, чтобы избежать дублирования
    logger.remove()

    if settings.DEBUG:
        # DEBUG-режим: цветной вывод в stderr с помощью функции-форматтера
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format=development_formatter,  # Используем функцию-форматтер
            # Фильтруем стандартные логи доступа uvicorn по имени логгера
            filter=lambda record: record["name"] != "uvicorn.access",
            colorize=True,  # Цветной вывод
            backtrace=True,  # Подробный трейсбек
            diagnose=True  # Диагностика переменных
        )
        logger.info("Логирование настроено для DEBUG-режима.")
    else:
        # DEBUG=False: JSON вывод в stderr
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            # serialize=True,  # Используем встроенную JSON сериализацию
            format=development_formatter,  # Используем функцию-форматтер TODO: Вернуть JSON
            colorize=True,  # Цветной вывод TODO: Remove
            filter=lambda record: record["name"] != "uvicorn.access",
            backtrace=False,  # Можно оставить True для детальности в JSON
            diagnose=False  # Диагностику в JSON не включаем
        )
        logger.info("Логирование настроено на JSON вывод в stderr.")

    # Файловый вывод (если включен PRODUCTION)
    log_file_path = settings.LOG_FILE_PATH

    if log_file_path:
        try:
            logger.add(
                log_file_path,
                rotation="100 MB",  # Ротация при достижении 100 MB
                retention="30 days",  # Хранить логи за последние 30 дней
                compression="zip",  # Сжимать старые логи
                level=settings.LOG_LEVEL,  # Уровень для записи в файл
                serialize=True,  # Используем встроенную JSON сериализацию
                enqueue=True,  # Асинхронная запись для производительности
                # Не фильтруем uvicorn.access для файла, т.к. там он может быть полезен
                backtrace=True,  # Пишем трейсбеки в файл
                diagnose=False  # Диагностику в файл не пишем
            )
            logger.info(f"Логирование в файл включено: {log_file_path}")
        except Exception as exc:
            logger.error(f"Ошибка настройки логирования в файл '{log_file_path}': {exc}", exc_info=True)
    else:
        logger.info("Логирование в файл отключено.")

    # Настройка логирования SQLAlchemy (только в DEBUG)
    if settings.DEBUG:
        logger.enable("sqlalchemy.engine")  # Включаем логгер SQLAlchemy
    else:
        logger.disable("sqlalchemy.engine")  # Отключаем SQL логи в production

    # Финальное сообщение о конфигурации
    logger.info(
        f"Loguru сконфигурирован. Уровень: {settings.LOG_LEVEL}. "
        f"Режим DEBUG: {settings.DEBUG}. "
        f"Логирование в файл: {'Включено' if log_file_path else 'Отключено'}."
    )


# Инициализация логирования при импорте модуля
configure_logging()

# Экспортируем настроенный логгер для использования в других модулях
log = logger
