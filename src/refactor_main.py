# src/main.py

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles # Нужен для монтирования медиа

from src.api.router import api_router
from src.core.config import settings
from src.core.database import db
from src.core.exceptions import setup_exception_handlers
from src.core.logging import log

# Определяем путь к директории со статикой UI
# Предполагаем, что main.py находится в src/, а static/ в src/static/
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
INDEX_HTML_PATH = os.path.join(STATIC_DIR, "index.html")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    Выполняет подключение к БД при старте и отключение при завершении.
    Также проверяет наличие статики UI.
    """
    log.info("Инициализация приложения...")
    try:
        # Проверяем наличие директории статики и index.html при старте
        if not os.path.isdir(STATIC_DIR):
            log.warning(f"Предупреждение: Директория статики UI '{STATIC_DIR}' не найдена!")
            # Не прерываем запуск, API все равно должен работать
        elif not os.path.isfile(INDEX_HTML_PATH):
            log.warning(f"Предупреждение: Файл '{INDEX_HTML_PATH}' не найден! SPA UI не будет работать.")
            # Не прерываем запуск
        else:
            log.info(f"Статика UI найдена в '{STATIC_DIR}'.")

        await db.connect()
        log.info("Подключение к БД установлено.")
        yield
    except Exception as exc:
        log.critical(f"Критическая ошибка при старте приложения: {exc}", exc_info=True)
        # Перевыбрасываем исключение, чтобы приложение не запустилось некорректно
        raise exc from exc
    finally:
        log.info("Остановка приложения...")
        await db.disconnect()
        log.info("Подключение к БД закрыто.")
        log.info("Приложение остановлено.")


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
        # Документация остается доступной по /docs и /redoc
    )

    # --- Настройка CORS ---
    # Позволяет фронтенду с другого домена обращаться к API
    if settings.DEBUG or not settings.PRODUCTION:
        allow_origins = ["*"]  # Разрешаем все для разработки/тестирования
        log.warning("CORS настроен разрешать все источники (*). Не используйте в production!")
    else:
        # TODO: Заменить на реальные разрешенные домены в production
        allow_origins = []  # По умолчанию запретить все, если не задано
        log.info(f"CORS настроен для production. Разрешенные источники: {allow_origins}")

    log.info("Настройка CORS...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Разрешить все стандартные методы (GET, POST, etc.)
        allow_headers=["*", settings.API_KEY_HEADER],  # Разрешить все заголовки + наш кастомный
    )
    log.info(f"CORS настроен. Разрешенный заголовок API ключа: '{settings.API_KEY_HEADER}'")

    # --- Настройка обработчиков исключений ---
    setup_exception_handlers(app)
    log.info("Обработчики исключений настроены.")

    # --- Подключение API роутера ---
    # API роуты должны быть определены ДО catch-all роута для SPA
    log.info("Подключение API роутера...")
    app.include_router(api_router, prefix="/api")

    # --- Монтируем статику для МЕДИА ---
    # Этот mount также должен идти ПЕРЕД catch-all роутом
    if settings.MEDIA_ROOT_PATH and settings.MEDIA_URL_PREFIX:
        media_dir = settings.MEDIA_ROOT_PATH
        media_url = settings.MEDIA_URL_PREFIX
        log.info(f"Монтирование медиа-статики: URL '{media_url}', Директория '{media_dir}'")
        if not os.path.isdir(media_dir):
            log.warning(f"Директория для медиа '{media_dir}' не существует. Медиа не будет раздаваться.")
        else:
            app.mount(media_url, StaticFiles(directory=media_dir), name="media")
    else:
        log.warning("Путь или URL-префикс для медиа не настроены.")

    # --- Catch-all роут для раздачи статики UI и SPA ---
    # ВАЖНО: Этот роут должен быть определен ПОСЛЕ всех специфичных роутов (API, media)
    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_spa_or_static(request: Request, full_path: str):
        """
        Обрабатывает GET запросы, не соответствующие API или медиа.
        Пытается найти и вернуть статический файл из STATIC_DIR.
        Если файл не найден или это путь без расширения (вероятно, путь SPA),
        возвращает INDEX_HTML_PATH для поддержки SPA.
        """
        # Проверяем наличие директории статики и index.html (на случай, если они не были найдены при старте)
        if not os.path.isdir(STATIC_DIR) or not os.path.isfile(INDEX_HTML_PATH):
             log.error("Статика UI или index.html не доступны.")
             return HTMLResponse(content="Internal Server Error: Frontend not available.", status_code=500)

        # Формируем путь к возможному статическому файлу
        # Нормализуем путь для безопасности
        static_file_path = os.path.normpath(os.path.join(STATIC_DIR, full_path))

        # Проверка на выход за пределы STATIC_DIR
        if not static_file_path.startswith(os.path.abspath(STATIC_DIR)):
            log.warning(f"Попытка доступа к файлу вне '{STATIC_DIR}': '{full_path}'")
            # Возвращаем index.html по умолчанию, чтобы не раскрывать структуру
            return FileResponse(INDEX_HTML_PATH)

        # Проверяем, существует ли файл и является ли он файлом
        # Также проверяем, имеет ли путь расширение (чтобы отличить файлы от путей SPA)
        if os.path.isfile(static_file_path) and "." in os.path.basename(static_file_path):
            log.debug(f"Обслуживание статического файла: '{static_file_path}'")
            return FileResponse(static_file_path)
        else:
            # Если файл не найден или путь похож на путь SPA (без расширения),
            # возвращаем index.html
            log.debug(f"Путь SPA или статический файл не найден: '{full_path}'. Возвращаем '{INDEX_HTML_PATH}'")
            return FileResponse(INDEX_HTML_PATH)

    log.info(f"Приложение '{settings.PROJECT_NAME}' сконфигурировано и готово к запуску.")
    return app


# Создаем приложение
app = create_app()