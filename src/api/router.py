"""Главный агрегатор API роутеров."""

from fastapi import APIRouter

from src.api.v1.router import router_v1
from src.core.config import settings

# Роутер, объединяющий все версии API
api_router = APIRouter()

# Подключаем роутер для v1 с префиксом из настроек
api_router.include_router(router_v1, prefix=settings.API_V1_STR)
