"""Модуль эндпоинтов для работы с твитами."""

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db_session
from app.core.exceptions import TweetValidationError
from app.models.user import User
from app.schemas.tweet import TweetCreate, TweetResponse
from app.services.tweet import TweetService

router = APIRouter(prefix="/tweets", tags=["tweets"])


@router.post(
    "/",
    response_model=TweetResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_tweet(
        tweet_data: TweetCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        db=Depends(get_db_session)
):
    """Создание нового твита.

    Args:
        tweet_data: Данные твита (текст + медиа)
        current_user: Текущий пользователь из API-ключа
        db: Сессия БД

    Returns:
        TweetResponse: Созданный твит

    Raises:
        TweetValidationError: При невалидных данных
    """
    service = TweetService(db)
    try:
        return await service.create_tweet(current_user.id, tweet_data)
    except ValueError as e:
        raise TweetValidationError(detail=str(e))