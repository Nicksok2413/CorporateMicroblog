"""Главный роутер для API версии v1."""

from fastapi import APIRouter

# Импортируем роутеры из поддиректории routes
from app.api.v1.routes import (
    media as media_routes,
    tweets as tweets_routes,
    likes as likes_routes,
    users as users_routes,
    follow as follow_routes
)

# Создаем главный роутер для v1
api_v1_router = APIRouter()

# Подключаем роутеры эндпоинтов
# Заметьте, что для likes и follow префиксы не указываем,
# так как полные пути (/tweets/{id}/likes, /users/{id}/follow)
# уже определены внутри их роутеров.
api_v1_router.include_router(media_routes.router)
api_v1_router.include_router(tweets_routes.router)
api_v1_router.include_router(likes_routes.router)
api_v1_router.include_router(users_routes.router)
api_v1_router.include_router(follow_routes.router)

# Альтернативный вариант для likes/follow (если бы пути в роутерах были относительные):
# api_v1_router.include_router(tweets_routes.router, prefix="/tweets")
# api_v1_router.include_router(likes_routes.router, prefix="/tweets") # ??? Не совсем корректно
# api_v1_router.include_router(users_routes.router, prefix="/users")
# api_v1_router.include_router(follow_routes.router, prefix="/users") # ??? Не совсем корректно

# Выбранный вариант с полными путями в likes/follow роутерах - самый простой в данном случае.