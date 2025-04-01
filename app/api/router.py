"""Главный роутер API, агрегирующий роутеры разных версий."""

from fastapi import APIRouter

# Импортируем роутер версии v1
from app.api.v1.router import router_v1

# Создаем главный роутер API
api_router = APIRouter()

# Подключаем роутер v1 с префиксом /v1
# Теперь все пути v1 будут начинаться с /api/v1/...
api_router.include_router(router_v1, prefix="/v1")

# Сюда можно будет добавить роутеры для других версий API в будущем
# from app.api.v2.router import router_v2
# api_router.include_router(router_v2, prefix="/v2")