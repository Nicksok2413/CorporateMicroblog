"""Главный API роутер."""

from fastapi import APIRouter

from src.api.routes import media, tweets, users

api_router = APIRouter()

# Включаем роутеры
api_router.include_router(media.router)
api_router.include_router(tweets.router)
api_router.include_router(users.router)
