"""Главный агрегатор API роутеров."""

from fastapi import APIRouter

from app.api.v1.router import router_v1  # Импортируем роутер v1
from app.core.config import settings  # Импортируем настройки для префикса

# Создаем главный роутер API
api_router = APIRouter()

# Подключаем роутер v1 с префиксом /v1
# Теперь все пути v1 будут начинаться с /api/v1/...
api_router.include_router(router_v1, prefix="/v1")
# api_router.include_router(router_v1, prefix=settings.API_V1_PREFIX)

# Сюда можно будет добавить роутеры для других версий API в будущем
# from app.api.v2.router import router_v2
# api_router.include_router(router_v2, prefix="/v2")
