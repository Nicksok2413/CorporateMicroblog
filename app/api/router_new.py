"""Главный агрегатор API роутеров."""

from fastapi import APIRouter
from app.api.v1.router_new import api_v1_router # Импортируем роутер v1
from app.core.config import settings # Импортируем настройки для префикса

# Главный роутер приложения
api_router = APIRouter()

# Подключаем роутер версии v1 с префиксом из настроек
api_router.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Здесь можно будет добавить v2 и т.д. в будущем
# from app.api.v2.router import api_v2_router
# api_router.include_router(api_v2_router, prefix="/api/v2")