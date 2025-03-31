"""Модуль для работы с API-ключами в корпоративной системе.

Содержит:
- Зависимость для проверки API-ключей
- Утилиты для демонстрационного режима
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository


async def get_current_user(
        api_key: Annotated[str, Header(alias=settings.API_KEY_HEADER)] = None,
        db: AsyncSession = Depends(get_db)
) -> User:
    """Зависимость для получения пользователя по API-ключу.

    Args:
        api_key: Ключ из HTTP-заголовка (любое значение)
        db: Асинхронная сессия БД

    Returns:
        User: Пользователь, найденный по ключу

    Raises:
        HTTPException: Если пользователь не найден (код 403)
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key header is required"
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_api_key(api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User with this API key not found"
        )

    return user


async def demo_mode_check(
        current_user: User = Depends(get_current_user)
) -> User:
    """Проверка, что пользователь в демо-режиме.

    Args:
        current_user: Текущий пользователь

    Returns:
        User: Тот же пользователь (для цепочки зависимостей)
    """
    if settings.PRODUCTION and current_user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo access restricted in production"
        )
    return current_user
