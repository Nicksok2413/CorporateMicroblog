"""Основной файл приложения FastAPI для сервиса микроблогов."""

# Сначала импортируем и настраиваем логирование
from app.core.logging import log

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.database import db
from app.core.exceptions import setup_exception_handlers  # Наша функция настройки обработчиков


# 3. Определяем lifespan для управления подключением к БД
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер жизненного цикла FastAPI.

    Выполняет подключение к БД при старте и отключение при остановке.

    Args:
        app: Экземпляр приложения FastAPI.

    Yields:
        None: В момент работы приложения.
    """
    log.info("Инициализация приложения...")
    try:
        await db.connect()  # Подключаемся к БД
        # Можно добавить другие действия при старте здесь
        # Если используете Alembic, можно добавить проверку/применение миграций при старте (опционально)
        # await run_migrations() # Пример функции для миграций
        log.info("Подключение к БД установлено.")
        yield  # Приложение готово к приему запросов и работает здесь
    except Exception as exc:
        log.critical(f"Критическая ошибка при старте приложения (БД?): {exc}", exc_info=True)
        # В зависимости от ошибки, возможно, стоит прервать запуск
        # raise exc
    finally:
        log.info("Остановка приложения...")
        await db.disconnect()  # Отключаемся от БД
        log.info("Подключение к БД закрыто.")
        log.info("Приложение остановлено.")


# 4. Создаем экземпляр FastAPI
log.info(f"Создание экземпляра FastAPI для '{settings.PROJECT_NAME} {settings.API_VERSION}'")
log.info(f"Debug={settings.DEBUG}, Testing={settings.TESTING}, Production={settings.PRODUCTION}")
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version=settings.API_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",  # Путь к схеме OpenAPI v1
    description="Бэкенд для корпоративного сервиса микроблогов",
    lifespan=lifespan,  # Подключаем управление жизненным циклом
)

# 5. Настраиваем CORS (Cross-Origin Resource Sharing)
# Позволяет фронтенду с другого домена обращаться к API
if settings.DEBUG or not settings.PRODUCTION:
    allow_origins = ["*"] # Разрешаем все для разработки/тестирования
    log.warning("CORS настроен разрешать все источники (*). Не используйте в production!")
else:
    # В production укажите конкретные разрешенные домены фронтенда
    # allow_origins = ["https://your-corporate-portal.com", "http://localhost:xxxx"] # Пример
    allow_origins = [] # По умолчанию запретить все, если не задано
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

# 6. Настраиваем обработчики исключений
setup_exception_handlers(app)
log.info("Обработчики исключений настроены.")

# 7. Подключаем роутеры API
log.info(f"Подключение API роутера с префиксом '{settings.API_V1_STR}'...")
app.include_router(api_router, prefix="/api")

# 8. Монтируем статические файлы для медиа
# URL будет /static/media/filename.jpg -> файл /app/static/media/filename.jpg
if settings.STORAGE_PATH_OBJ and settings.STORAGE_PATH_OBJ.is_dir():
    # Префикс URL, по которому будут доступны файлы (/static/media/filename.jpg)
    media_url_prefix = settings.MEDIA_URL_PREFIX
    # Имя для внутреннего использования FastAPI
    media_static_name = "media_files"
    # Путь к директории с файлами
    media_directory = settings.STORAGE_PATH_OBJ

    log.info(f"Монтирование статики: URL '{media_url_prefix}' -> Директория '{settings.STORAGE_PATH_OBJ}'")
    app.mount(media_url_prefix, StaticFiles(directory=settings.media_directory), name=media_static_name)
else:
    log.warning(f"Директория для медиафайлов '{settings.STORAGE_PATH}' не найдена или не настроена."
                f" Раздача медиа будет недоступна.")

# 9. Корневой эндпоинт для проверки
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
