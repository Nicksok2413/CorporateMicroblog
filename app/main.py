"""Основной файл приложения FastAPI для сервиса микроблогов."""

# 1. Сначала импортируем и настраиваем логирование
from app.core.logging import log, configure_logging
# configure_logging() # Loguru обычно настраивается при импорте, вызов не обязателен

# 2. Импортируем остальные компоненты ядра и FastAPI
import logging
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
        yield  # Приложение готово к приему запросов и работает здесь
    except Exception as exc:
        log.critical(f"Критическая ошибка при старте приложения (БД?): {exc}", exc_info=True)
        # В зависимости от ошибки, возможно, стоит прервать запуск
        # raise e
    finally:
        log.info("Остановка приложения...")
        await db.disconnect()  # Отключаемся от БД
        # Можно добавить другие действия при остановке здесь
        log.info("Приложение остановлено.")


# 4. Создаем экземпляр FastAPI
log.info(f"Создание экземпляра FastAPI для '{settings.PROJECT_NAME}'")
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,  # Передаем режим отладки
    version="1.0.0",  # Версия вашего API
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",  # Путь к схеме OpenAPI v1
    description="Бэкенд для корпоративного сервиса микроблогов",
    lifespan=lifespan,  # Подключаем управление жизненным циклом
    # Дополнительные параметры FastAPI при необходимости...
    # docs_url="/docs", redoc_url="/redoc" - по умолчанию
)

# 5. Настраиваем CORS (Cross-Origin Resource Sharing)
# Позволяет фронтенду с другого домена обращаться к API
log.info("Настройка CORS...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (небезопасно для production!)
    # В production укажите конкретные домены фронтенда:
    # allow_origins=["http://localhost:3000", "https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все стандартные методы (GET, POST, etc.)
    allow_headers=["*", settings.API_KEY_HEADER],  # Разрешить все заголовки + наш кастомный
)
log.info(f"CORS настроен. Разрешенные заголовки включают: {settings.API_KEY_HEADER}")

# 6. Настраиваем обработчики исключений
setup_exception_handlers(app)

# 7. Подключаем роутеры API
log.info(f"Подключение API роутеров с префиксом '{settings.API_V1_PREFIX}'...")
# Убедитесь, что ваш api_router ожидает этот префикс
# Если роуты внутри api_router УЖЕ имеют префикс /v1, то здесь префикс не нужен.
# Если api_router - это агрегатор для /v1, /v2 и т.д., то префикс нужен здесь.
# Судя по вашей структуре (api/router.py -> api/v1/...), префикс нужен здесь.
app.include_router(api_router, prefix="/api")  # Например /api/v1/users...

# 8. Монтируем статические файлы для медиа
# URL будет /static/media/filename.jpg -> файл /app/static/media/filename.jpg
if settings.STORAGE_PATH_OBJ:
    media_url_prefix = "/static/media"  # Можно взять из настроек, если нужно
    log.info(f"Монтирование статики: URL '{media_url_prefix}' -> Директория '{settings.STORAGE_PATH_OBJ}'")
    app.mount(media_url_prefix, StaticFiles(directory=settings.STORAGE_PATH_OBJ), name="media_files")
else:
    log.warning("Директория для медиафайлов (STORAGE_PATH_OBJ) не настроена.")


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
        "documentation_urls": ["/docs", "/redoc"]
    }


log.info(f"Приложение '{settings.PROJECT_NAME}' сконфигурировано и готово к запуску.")

# Заметка: Запуск приложения обычно происходит через uvicorn в командной строке или Docker,
# поэтому блок `if __name__ == "__main__": uvicorn.run(...)` здесь не обязателен.
