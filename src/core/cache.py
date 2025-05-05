"""Настройка Redis."""

from typing import Optional

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from src.core.logging import log

# Тип для клиента, чтобы не импортировать везде
RedisClientType = aioredis.Redis

# Константы
REDIS_HOST = "redis"  # Хост Redis
REDIS_PORT = 6379  # Порт Redis
REDIS_PASSWORD = ""  # Пароль Redis (Опционально)
REDIS_DB = 0  # Номер базы данных Redis

# URL для подключения к Redis
password = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
redis_url = f"redis://{password}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"


async def initialize_cache() -> Optional[RedisClientType]:
    """
    Инициализирует соединение с Redis и бэкенд для fastapi-cache.

    Returns:
        Optional[aioredis.Redis]: Клиент Redis в случае успеха, иначе None.
    """
    log.info(f"Попытка подключения к Redis и инициализации кэша: {redis_url}")
    redis_client = None

    try:
        redis_client = aioredis.from_url(
            redis_url, encoding="utf8", decode_responses=True
        )
        await redis_client.ping()
        log.success("Успешное подключение к Redis.")

        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
        log.info('FastAPI-Cache инициализирован с Redis бэкендом.')

        # Возвращаем клиент, чтобы lifespan мог его закрыть
        return redis_client

    except Exception as exc:
        log.exception(f"Не удалось подключиться к Redis или инициализировать кэш: {exc}")

        # Закрываем соединение, если оно было создано до ошибки
        if redis_client:
            try:
                await redis_client.close()
            except Exception as close_exc:
                log.error(f"Ошибка при закрытии Redis после неудачной инициализации: {close_exc}")

        return None  # Возвращаем None при ошибке


async def close_redis_connection(redis_client: Optional[RedisClientType]) -> None:
    """
    Закрывает переданное соединение с Redis, если оно существует.

    Args:
        redis_client: Экземпляр клиента Redis или None.
    """
    if redis_client:
        log.info("Закрытие соединения с Redis...")
        try:
            await redis_client.close()
            log.info("Соединение с Redis успешно закрыто.")
        except Exception as exc:
            log.exception(f"Ошибка при закрытии соединения с Redis: {exc}")
