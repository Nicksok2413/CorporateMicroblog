"""Агрегация роутеров для API версии v1."""

from fastapi import APIRouter

# Импортируем роутеры из подмодулей routes
from app.api.v1.routes import users, tweets, media  # Импорт по именам файлов

# Создаем главный роутер для v1
router_v1 = APIRouter()

# Включаем роутеры с их префиксами
router_v1.include_router(users.router)  # Префикс /users уже задан в users.router
router_v1.include_router(tweets.router)  # Префикс /tweets уже задан в tweets.router
router_v1.include_router(media.router)  # Префикс /media уже задан в media.router

# Можно добавить здесь общие зависимости или параметры для всех роутов v1, если нужно
