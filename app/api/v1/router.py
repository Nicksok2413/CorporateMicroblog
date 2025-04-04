"""Агрегация роутеров для API версии v1."""

from fastapi import APIRouter

from app.api.v1.routes import follow, likes, media, tweets, users   # Импорт по именам файлов

# Создаем главный роутер для v1
router_v1 = APIRouter()

# Включаем роутеры с их префиксами
router_v1.include_router(follow.router)  # Полный путь `/users/{id}/follow` уже задан в follow.router
router_v1.include_router(likes.router)  # Полный путь `/tweets/{id}/likes` уже задан в likes.router
router_v1.include_router(media.router)  # Префикс /media уже задан в media.router
router_v1.include_router(tweets.router)  # Префикс /tweets уже задан в tweets.router
router_v1.include_router(users.router)  # Префикс /users уже задан в users.router
