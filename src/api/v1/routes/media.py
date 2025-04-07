"""API роуты для работы с медиафайлами."""

from typing import Optional

from fastapi import APIRouter, File, UploadFile, status

from src.api.v1.dependencies import CurrentUser, DBSession, MediaSvc
from src.core.logging import log
from src.schemas.media import MediaCreateResult

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    "",
    response_model=MediaCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузка медиафайла",
    description="Загружает медиафайл (изображение) и возвращает его ID для последующего прикрепления к твиту.",
)
async def upload_media_file(
        db: DBSession,
        current_user: CurrentUser,
        media_service: MediaSvc,
        # Данные файла из формы (multipart/form-data)
        file: UploadFile = File(..., description="Медиафайл для загрузки (jpg, png, gif)")
) -> Optional[MediaCreateResult]:
    """
    Обрабатывает загрузку медиафайла.

    - Проверяет авторизацию пользователя.
    - Валидирует и сохраняет файл с помощью `media_service`.
    - Создает запись в БД.
    - Возвращает ID созданного медиафайла.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        media_service (MediaSvc): Экземпляр сервиса `MediaService`.
        file (UploadFile): Загружаемый файл.

    Returns:
        Optional[MediaCreateResult]: Результат с ID созданного медиа или None.

    Raises:
        MediaValidationError: Если файл не прошел валидацию (перехватывается обработчиком).
        BadRequestError: Если произошла ошибка сохранения файла или БД (перехватывается).
    """
    log.info(f"Пользователь ID {current_user.id} загружает файл: '{file.filename}' ({file.content_type})")
    media = None

    try:
        media = await media_service.save_media_file(
            db=db,
            file=file.file,  # Передаем сам файловый объект
            filename=file.filename or "unknown",  # Используем имя файла или заглушку
            content_type=file.content_type or "application/octet-stream"
        )
    except Exception:
        log.exception(f"Ошибка при обработке загрузки файла от пользователя ID {current_user.id}")
        raise
    finally:
        await file.close()
        log.debug(f"Файл '{file.filename}' закрыт после обработки.")

    return MediaCreateResult(media_id=media.id)
