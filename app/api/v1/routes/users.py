"""Эндпоинты для работы с профилями пользователей."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db_session
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserDetailResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserDetailResponse
)
async def get_my_profile(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Получить профиль текущего пользователя.

    Args:
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        UserDetailResponse: Полная информация о профиле

    Raises:
        HTTPException: Если пользователь не найден
    """
    service = UserService(db)
    try:
        return await service.get_current_user_profile(current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{user_id}",
    response_model=UserProfileResponse
)
async def get_user_profile(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Получить профиль другого пользователя.

    Args:
        user_id: ID целевого пользователя
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        UserProfileResponse: Основная информация о профиле

    Raises:
        HTTPException: Если пользователь не найден
    """
    service = UserService(db)
    try:
        return await service.get_user_profile(current_user.id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
