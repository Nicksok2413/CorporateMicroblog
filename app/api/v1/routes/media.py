"""Эндпоинты для работы с медиафайлами."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.media import MediaResponse
from app.services.media import MediaService

router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "/",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_media_file(
        file: UploadFile,
        current_user: User = Depends(get_current_user),
        db=Depends(get_db)
):
    """Загрузка медиафайла.

    Args:
        file: Файл для загрузки
        current_user: Авторизованный пользователь
        db: Сессия БД

    Returns:
        MediaResponse: Информация о загруженном файле

    Raises:
        HTTPException: При ошибках валидации файла
    """
    service = MediaService(db)
    try:
        media = await service.upload_file(
            user_id=current_user.id,
            file=file
        )
        return MediaResponse(
            id=media.id,
            url=media.url
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )