"""Эндпоинты для работы с подписками."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db_session
from app.models.user import User
from app.schemas.follow import FollowResponse, UserFollowStats
from app.services.follow import FollowService

router = APIRouter(prefix="/users", tags=["follow"])


@router.post(
    "/{user_id}/follow",
    response_model=FollowResponse,
    status_code=status.HTTP_201_CREATED
)
async def follow_user(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Подписаться на пользователя.

    Args:
        user_id: ID пользователя для подписки
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FollowResponse: Статистика подписок

    Raises:
        HTTPException: При ошибках валидации
    """
    service = FollowService(db)
    try:
        return await service.follow_user(current_user.id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{user_id}/follow",
    response_model=FollowResponse
)
async def unfollow_user(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Отписаться от пользователя.

    Args:
        user_id: ID пользователя для отписки
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FollowResponse: Статистика подписок

    Raises:
        HTTPException: Если подписка не найдена
    """
    service = FollowService(db)
    try:
        return await service.unfollow_user(current_user.id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{user_id}/follow",
    response_model=FollowResponse
)
async def get_follow_status(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Проверить статус подписки.

    Args:
        user_id: ID целевого пользователя
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        FollowResponse: Статистика подписок
    """
    service = FollowService(db)
    return await service.get_follow_stats(current_user.id, user_id)


@router.get(
    "/{user_id}/follow/stats",
    response_model=UserFollowStats
)
async def get_user_follow_stats(
        user_id: int,
        db: AsyncSession = Depends(get_db_session)
):
    """Получить детальную статистику подписок.

    Args:
        user_id: ID пользователя
        db: Сессия БД

    Returns:
        UserFollowStats: Списки подписчиков и подписок
    """
    service = FollowService(db)
    return await service.get_user_follow_stats(user_id)
