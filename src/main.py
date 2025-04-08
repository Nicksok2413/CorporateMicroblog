"""Основной файл приложения FastAPI для сервиса микроблогов."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.router import api_router
from src.core.config import settings
from src.core.database import db
from src.core.exceptions import setup_exception_handlers
from src.core.logging import log


# Определяем lifespan для управления подключением к БД
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    Выполняет подключение к БД при старте и отключение при завершении.
    """
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
    if settings.DEBUG or not settings.PRODUCTION:
        allow_origins = ["*"]  # Разрешаем все для разработки/тестирования
        log.warning("CORS настроен разрешать все источники (*). Не используйте в production!")
    else:
        # allow_origins = ["https://your-corporate-portal.com", "http://localhost:xxxx"] # Пример
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

    # Настраиваем обработчики исключений
    setup_exception_handlers(app)
    log.info("Обработчики исключений настроены.")

    # Подключаем API роутер
    log.info(f"Подключение API роутера...")
    app.include_router(api_router, prefix="/api")  # Префикс /api для всех эндпоинтов

    # Монтируем статические файлы для медиа
    if settings.MEDIA_ROOT_PATH:
        log.info(f"Монтирование статики: URL '{settings.MEDIA_URL_PREFIX}', "
                 f"Директория '{settings.MEDIA_ROOT_PATH}'")
        app.mount(
            settings.MEDIA_URL_PREFIX,
            StaticFiles(directory=settings.MEDIA_ROOT_PATH),
            name="media")  # Имя для возможности генерации URL через url_for
    else:
        log.warning(f"Директория для медиафайлов '{settings.STORAGE_PATH}' не найдена или не настроена.")

    # Можно добавить монтирование для "общей" статики фронтенда, если нужно
    # app.mount("/static", StaticFiles(directory="src/static"), name="static")

    # Корневой эндпоинт для проверки
    @app.get("/", tags=["Default"], summary="Проверка доступности сервиса")
    async def root():
        """
        Корневой эндпоинт.

        Возвращает приветственное сообщение и информацию о доступности документации.
        """
        log.debug("Запрос к корневому эндпоинту '/'")
        return {
            "message": f"Добро пожаловать в {settings.PROJECT_NAME}!",
            "api_version": f"{settings.API_VERSION}",
            "documentation_swagger": "/docs",
            "documentation_redoc": "/redoc",
            "status": "operational",
            "debug_mode": settings.DEBUG,
        }

    log.info(f"Приложение '{settings.PROJECT_NAME}' сконфигурировано и готово к запуску.")
    return app


# Создаем приложение
app = create_app()
