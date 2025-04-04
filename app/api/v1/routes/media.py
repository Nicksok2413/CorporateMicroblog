"""API роуты для работы с медиафайлами."""

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.v1.dependencies import CurrentUser, DBSession, MediaSvc, get_media_service
from app.core.exceptions import BadRequestError
from app.core.logging import log
from app.services import MediaService
from app.schemas import MediaCreateResult

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    "",
    response_model=MediaCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузка медиафайла",
    description="Загружает медиафайл (изображение) и возвращает его ID для последующего прикрепления к твиту.",
)
async def upload_media_file(
        current_user: CurrentUser,
        db: DBSession,
        media_service: MediaSvc,
        # Данные файла из формы (multipart/form-data)
        file: UploadFile = File(..., description="Медиафайл для загрузки (jpg, png, gif)")
):
    """
    Обрабатывает загрузку медиафайла.

    - Проверяет авторизацию пользователя.
    - Валидирует и сохраняет файл с помощью `media_service`.
    - Создает запись в БД.
    - Возвращает ID созданного медиафайла.

    Args:
        current_user: Аутентифицированный пользователь (инъекция).
        db: Сессия БД (инъекция).
        file: Загружаемый файл (инъекция).

    Returns:
        MediaCreateResult: Результат с ID созданного медиа.

    Raises:
        MediaValidationError: Если файл не прошел валидацию (перехватывается обработчиком).
        BadRequestError: Если произошла ошибка сохранения файла или БД (перехватывается).
    """
    log.info(f"Пользователь ID {current_user.id} загружает файл: '{file.filename}' ({file.content_type})")

    try:
        media = await media_service.save_media_file(
            db=db,
            file=file.file,  # Передаем сам файловый объект
            filename=file.filename or "unknown",  # Используем имя файла или заглушку
            content_type=file.content_type or "application/octet-stream"
        )
    except Exception as exc:
        # Логируем ошибку и позволяем обработчику исключений FastAPI разобраться
        log.exception(f"Непредвиденная ошибка при обработке загрузки файла от пользователя ID {current_user.id}")
        # Перевыбрасываем как BadRequestError или позволяем обработчику поймать оригинальное исключение
        raise BadRequestError(f"Ошибка при обработке файла: {exc}") from exc
    finally:
        await file.close()
        log.debug(f"Файл '{file.filename}' закрыт после обработки.")

    return MediaCreateResult(media_id=media.id)
