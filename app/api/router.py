"""Главный агрегатор API роутеров."""

from fastapi import APIRouter

from app.api.v1.router import router_v1  # Импортируем роутер v1
from app.core.config import settings  # Импортируем настройки для префикса

# Создаем главный роутер API
api_router = APIRouter()

# Подключаем роутер v1 с префиксом /v1
api_router.include_router(router_v1, prefix=settings.API_V1_STR)
