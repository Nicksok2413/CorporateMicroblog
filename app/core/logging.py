import json
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def serialize(record):
    """Кастомная сериализация для JSON-логов"""
    subset = {
        "timestamp": record["time"].timestamp(),
        "message": record["message"],
        "level": record["level"].name,
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    if "extra" in record and record["extra"]:
        subset.update(record["extra"])
    return json.dumps(subset)


def formatter(record):
    """Форматтер для консольного вывода"""
    if settings.PRODUCTION:
        return serialize(record)
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )


def configure_logging():
    """Настройка Loguru с ротацией логов и фильтрацией"""

    # Удаляем стандартный обработчик
    logger.remove()

    # Консольный вывод (все уровни в dev, только WARNING+ в production)
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=formatter,
        filter=lambda record: "uvicorn.access" not in record["extra"],
        colorize=True,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG
    )

    # Файловый вывод (только для production)
    if settings.PRODUCTION:
        log_path = Path("logs") / "app_{time}.log"
        logger.add(
            log_path,
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            level="INFO",
            format=serialize,
            enqueue=True  # Асинхронная запись
        )

    # SQLAlchemy логи (только в DEBUG)
    if settings.DEBUG:
        logger.add(
            sys.stderr,
            level="INFO",
            filter=lambda record: "sqlalchemy" in record["extra"],
            format="<magenta>SQL:</magenta> {message}",
            colorize=True
        )


# Инициализация при импорте
configure_logging()

# Для удобного импорта
log = logger
