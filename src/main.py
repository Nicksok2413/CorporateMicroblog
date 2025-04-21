"""Основной файл приложения FastAPI для сервиса микроблогов."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.router import api_router
from src.core.config import settings
from src.core.database import db
from src.core.exceptions import setup_exception_handlers
from src.core.logging import log

# Путь к директории со статикой фронтенда
STATIC_FILES_DIR = os.path.join(os.path.dirname(__file__), "static")
# Путь к index.html
INDEX_HTML_PATH = os.path.join(STATIC_FILES_DIR, "index.html")


# Определяем lifespan для управления подключением к БД
@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    Выполняет подключение к БД при старте и отключение при завершении.
    """
    log.info("Инициализация приложения...")
    try:
        await db.connect()
        yield
    except Exception as exc:
        log.critical(f"Критическая ошибка при старте приложения (БД?): {exc}", exc_info=True)
        raise exc
    finally:
        log.info("Остановка приложения...")
        await db.disconnect()
        log.info("Приложение остановлено.")


# Создаем экземпляр FastAPI
def create_app() -> FastAPI:
    """Создает и конфигурирует экземпляр приложения FastAPI."""
    log.info(f"Создание экземпляра FastAPI для '{settings.PROJECT_NAME} {settings.API_VERSION}'")
    log.info(f"Debug={settings.DEBUG}, Testing={settings.TESTING}, Production={settings.PRODUCTION}")

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        description="Бэкенд для корпоративного сервиса микроблогов",
    )

    # Настраиваем CORS (Cross-Origin Resource Sharing)
    # Позволяет фронтенду с другого домена обращаться к API
    if not settings.PRODUCTION:
        allow_origins = ["*"]  # Разрешаем все для разработки/тестирования
        log.warning("CORS настроен разрешать все источники (*). Не использовать в PRODUCTION!")
    else:
        # TODO: Заменить на реальные разрешенные домены в production
        allow_origins = []  # По умолчанию запретить все, если не задано
        log.info(f"CORS настроен для PRODUCTION. Разрешенные источники: {allow_origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Разрешить все стандартные методы (GET, POST, etc.)
        allow_headers=["*", settings.API_KEY_HEADER],  # Разрешить все заголовки + наш кастомный
    )

    # Настраиваем обработчики исключений
    setup_exception_handlers(app)
    log.info("Обработчики исключений настроены.")

    # Подключаем API роутер
    log.info("Подключение API роутера...")
    app.include_router(api_router, prefix="/api")

    # Монтируем статические файлы для медиа
    log.info(f"Монтирование статики: URL '{settings.MEDIA_URL_PREFIX}', Директория '{settings.MEDIA_ROOT_PATH}'")
    app.mount(
        settings.MEDIA_URL_PREFIX,
        StaticFiles(directory=settings.MEDIA_ROOT_PATH),
        name="media",
    )

    # Монтируем статику фронтенда
    log.info(f"Монтирование статики фронтенда из '{STATIC_FILES_DIR}' по пути '/'")
    app.mount(
        "/",
        StaticFiles(directory=STATIC_FILES_DIR, html=True),
        name="static_frontend",
    )

    # Catch-all: Обработчик для корневого пути (и всех остальных, не пойманных ранее),
    # чтобы всегда возвращать index.html для SPA
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        Отдает index.html для любого пути, не обработанного ранее.
        Необходимо для корректной работы роутинга в SPA (Vue Router).
        """
        # Проверяем, существует ли index.html
        if not os.path.exists(INDEX_HTML_PATH):
            log.error(f"Файл index.html не найден по пути: {INDEX_HTML_PATH}")
            return {"error": "Frontend entrypoint not found"}, 500

        log.debug(f"Путь '{full_path}' не найден, отдаем SPA index.html")
        return FileResponse(INDEX_HTML_PATH)

    log.info(f"Приложение '{settings.PROJECT_NAME} {settings.API_VERSION}' сконфигурировано и готово к запуску.")
    return app


# Создаем приложение
app = create_app()
