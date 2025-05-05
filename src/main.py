"""Основной файл приложения FastAPI для сервиса микроблогов."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics

from src.api.router import api_router
from src.core.cache import RedisClientType, initialize_cache, close_redis_connection
from src.core.config import settings
from src.core.database import db
from src.core.exceptions import setup_exception_handlers
from src.core.logging import log
from src.core.sentry import initialize_sentry

# Вызываем инициализацию Sentry
initialize_sentry()


# Определяем lifespan для управления подключением к Redis и БД
@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    Выполняет подключение к БД при старте и отключение при завершении.
    """
    log.info("Инициализация приложения...")
    # Переменные для хранения состояний ресурсов
    redis_client: Optional[RedisClientType] = None
    db_connected = False

    try:
        # Инициализация Redis и Кэша
        redis_client = await initialize_cache()
        # Инициализация подключения к БД
        await db.connect()
        db_connected = True
        # Приложение готово к работе
        yield
    except Exception as exc:
        log.critical(f"Критическая ошибка: {exc}", exc_info=True)
        raise exc
    finally:
        log.info("Остановка приложения...")
        # # Закрываем соединение с Redis
        await close_redis_connection(redis_client)
        # Закрываем соединение с БД, если оно было установлено
        if db_connected:
            await db.disconnect()
        log.info("Приложение остановлено.")


# Создаем экземпляр FastAPI
def create_app() -> FastAPI:
    """Создает и конфигурирует экземпляр приложения FastAPI."""
    log.info(
        f"Создание экземпляра FastAPI для '{settings.PROJECT_NAME} {settings.API_VERSION}'"
    )
    log.info(
        f"Debug={settings.DEBUG}, Testing={settings.TESTING}, Production={settings.PRODUCTION}"
    )

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        description="Бэкенд для корпоративного сервиса микроблогов",
    )

    # Добавляем middleware для Prometheus
    app.add_middleware(PrometheusMiddleware, app_name="microblog_fastapi")
    # Добавляем роут для эндпоинта /metrics
    app.add_route("/metrics", handle_metrics)
    log.info("PrometheusMiddleware и эндпоинт /metrics добавлены.")

    # Настраиваем CORS (Cross-Origin Resource Sharing)
    # Позволяет фронтенду с другого домена обращаться к API
    if not settings.PRODUCTION:  # type: ignore[truthy-function]
        allow_origins: list[str] = ["*"]  # Разрешаем все для разработки/тестирования
        log.warning(
            "CORS настроен разрешать все источники (*). Не использовать в PRODUCTION!"
        )
    else:  # pragma: no cover
        allow_origins = []  # По умолчанию запретить все, если не задано
        log.info(
            f"CORS настроен для PRODUCTION. Разрешенные источники: {allow_origins}"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Разрешить все стандартные методы (GET, POST, etc.)
        allow_headers=[
            "*",
            settings.API_KEY_HEADER,
        ],  # Разрешить все заголовки + наш кастомный
    )

    # Настраиваем обработчики исключений
    setup_exception_handlers(app)
    log.info("Обработчики исключений настроены.")

    # Подключаем API роутер
    log.info("Подключение API роутера...")
    app.include_router(api_router, prefix="/api")

    log.info(
        f"Приложение '{settings.PROJECT_NAME} {settings.API_VERSION}' сконфигурировано и готово к запуску."
    )
    return app


# Создаем приложение
app = create_app()
