# src/main.py

import os # Добавить импорт os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse # Добавить импорт FileResponse

from src.api.router import api_router
from src.core.config import settings
from src.core.database import db
from src.core.exceptions import setup_exception_handlers
from src.core.logging import log


# Lifespan остается без изменений
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Инициализация приложения...")
    try:
        await db.connect()
        log.info("Подключение к БД установлено.")
        yield
    except Exception as exc:
        log.critical(f"Критическая ошибка при старте приложения (БД?): {exc}", exc_info=True)
        raise exc
    finally:
        log.info("Остановка приложения...")
        await db.disconnect()
        log.info("Подключение к БД закрыто.")
        log.info("Приложение остановлено.")


# Путь к директории со статикой фронтенда
STATIC_FILES_DIR = os.path.join(os.path.dirname(__file__), "static")
# Путь к index.html
INDEX_HTML_PATH = os.path.join(STATIC_FILES_DIR, "index.html")


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
        # Убираем стандартные /docs и /redoc, если фронтенд использует эти пути,
        # или оставляем, если они не конфликтуют. По умолчанию оставим.
        # docs_url=None,
        # redoc_url=None,
    )

    # Настраиваем CORS (остается без изменений)
    # ... (код CORS middleware) ...
    if settings.DEBUG or not settings.PRODUCTION:
        allow_origins = ["*"]
        log.warning("CORS настроен разрешать все источники (*). Не используйте в production!")
    else:
        allow_origins = []
        log.info(f"CORS настроен для production. Разрешенные источники: {allow_origins}")

    log.info("Настройка CORS...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", settings.API_KEY_HEADER],
    )
    log.info(f"CORS настроен. Разрешенный заголовок API ключа: '{settings.API_KEY_HEADER}'")

    # Настраиваем обработчики исключений (остается без изменений)
    setup_exception_handlers(app)
    log.info("Обработчики исключений настроены.")

    # Подключаем API роутер (остается без изменений)
    log.info("Подключение API роутера...")
    app.include_router(api_router, prefix="/api")

    # Монтируем статику для медиа (остается без изменений)
    if settings.MEDIA_ROOT_PATH:
        log.info(f"Монтирование статики медиа: URL '{settings.MEDIA_URL_PREFIX}', "
                 f"Директория '{settings.MEDIA_ROOT_PATH}'")
        app.mount(
            settings.MEDIA_URL_PREFIX,
            StaticFiles(directory=settings.MEDIA_ROOT_PATH),
            name="media")
    else:
        log.warning("Директория для медиафайлов не настроена.")

    # --- НОВОЕ: Монтирование статики фронтенда ---
    log.info(f"Монтирование статики фронтенда из '{STATIC_FILES_DIR}' по пути '/'")
    app.mount(
        "/",
        StaticFiles(directory=STATIC_FILES_DIR, html=True), # html=True для обслуживания index.html
        name="static_frontend"
    )

    # --- ИЗМЕНЕНО: Обработчик для корневого пути (и всех остальных, не пойманных ранее),
    # чтобы всегда возвращать index.html для SPA ---
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        Отдает index.html для любого пути, не обработанного ранее.
        Необходимо для корректной работы роутинга в SPA (Vue Router).
        """
        # Проверяем, существует ли index.html
        if not os.path.exists(INDEX_HTML_PATH):
            log.error(f"Файл index.html не найден по пути: {INDEX_HTML_PATH}")
            return {"error": "Frontend entrypoint not found"}, 500 # или другое сообщение

        log.debug(f"Путь '{full_path}' не найден, отдаем SPA index.html")
        return FileResponse(INDEX_HTML_PATH)

    log.info(f"Приложение '{settings.PROJECT_NAME}' сконфигурировано и готово к запуску.")
    return app

# Создаем приложение (остается без изменений)
app = create_app()