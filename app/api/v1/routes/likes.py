"""Эндпоинты для работы с лайками."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.like import LikeResponse
from app.services.like import LikeService

router = APIRouter(prefix="/tweets", tags=["likes"])


@router.post(
    "/{tweet_id}/likes",
    response_model=LikeResponse,
    status_code=status.HTTP_201_CREATED
)
async def like_tweet(
        tweet_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Поставить лайк твиту.

    Args:
        tweet_id: ID твита
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        LikeResponse: Информация о лайках

    Raises:
        HTTPException: Если лайк уже поставлен
    """
    service = LikeService(db)
    try:
        return await service.like_tweet(current_user.id, tweet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{tweet_id}/likes",
    response_model=LikeResponse
)
async def unlike_tweet(
        tweet_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Убрать лайк с твита.

    Args:
        tweet_id: ID твита
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        LikeResponse: Информация о лайках

    Raises:
        HTTPException: Если лайк не найден
    """
    service = LikeService(db)
    try:
        return await service.unlike_tweet(current_user.id, tweet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
