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

# v2
# """API эндпоинты для работы с медиа."""
#
# from fastapi import APIRouter, Depends, UploadFile, HTTPException
# from fastapi.responses import FileResponse
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from app.core.database import get_db
# from app.core.security import get_current_user
# from app.models.user import User
# from app.services.media import MediaService
# from app.schemas.media import MediaResponse
#
# router = APIRouter(prefix="/media", tags=["media"])
#
#
# @router.post("", response_model=MediaResponse)
# async def upload_media(
#         file: UploadFile,
#         current_user: User = Depends(get_current_user),
#         db: AsyncSession = Depends(get_db)
# ):
#     """
#     Загрузка нового медиафайла.
#
#     Returns:
#         MediaResponse: Информация о загруженном файле
#     """
#     service = MediaService(db)
#     media = await service.upload_file(current_user.id, file)
#     return MediaService.to_response(media)
#
#
# @router.get("/files/{filename}")
# async def get_media_file(filename: str):
#     """
#     Получение медиафайла по имени.
#
#     Returns:
#         FileResponse: Файловый ответ
#     """
#     file_path = Path(settings.STORAGE_PATH) / filename
#     if not file_path.exists():
#         raise HTTPException(status_code=404, detail="Файл не найден")
#     return FileResponse(file_path)
#
#
# @router.delete("/{media_id}")
# async def delete_media(
#         media_id: int,
#         current_user: User = Depends(get_current_user),
#         db: AsyncSession = Depends(get_db)
# ):
#     """
#     Удаление медиафайла.
#
#     Returns:
#         dict: Результат операции
#     """
#     service = MediaService(db)
#     media = await service.get_media_by_id(media_id)
#
#     if not media:
#         raise HTTPException(status_code=404, detail="Медиа не найдено")
#
#     if media.user_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Недостаточно прав")
#
#     await service.delete_media(media)
#     return {"result": True}