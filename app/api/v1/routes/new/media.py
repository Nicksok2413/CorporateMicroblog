"""API роуты для загрузки медиафайлов."""

from fastapi import APIRouter, Depends, File, UploadFile, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.schemas import MediaCreateResult # Схема ответа
from app.services import media_service # Сервис для работы с медиа

# Создаем роутер для медиа
# Тэги используются для группировки в Swagger UI
router = APIRouter(tags=["Media"])


@router.post(
    # URL для этого эндпоинта будет /api/v1/medias (префиксы добавятся позже)
    "/medias",
    response_model=MediaCreateResult,
    status_code=status.HTTP_201_CREATED, # Статус 201 Created для успешного создания ресурса
    summary="Загрузка медиафайла",
    description="Загружает файл (изображение) и возвращает его ID для последующего прикрепления к твиту.",
)
async def upload_media(
    # Зависимости: текущий пользователь и сессия БД
    current_user: CurrentUser, # Проверяет аутентификацию
    db: DBSession,
    # Параметр для загрузки файла
    file: UploadFile = File(..., description="Файл для загрузки (jpg, png, gif)")
):
    """
    Обрабатывает загрузку медиафайла.

    - Валидирует файл (через media_service).
    - Сохраняет файл (через media_service).
    - Создает запись в БД (через media_service).

    Args:
        current_user: Аутентифицированный пользователь (инъекция зависимости).
        db: Сессия базы данных (инъекция зависимости).
        file: Загружаемый файл (из формы).

    Returns:
        MediaCreateResult: Результат с ID созданного медиафайла.

    Raises:
        MediaValidationError: Если файл не прошел валидацию.
        BadRequestError: При ошибках сохранения файла или записи в БД.
        AuthenticationRequiredError: Если не предоставлен api-key.
        PermissionDeniedError: Если api-key невалиден.
    """
    log.info(f"Запрос на загрузку медиафайла от пользователя ID {current_user.id}. Имя файла: '{file.filename}'")
    # Вызываем метод сервиса для сохранения файла
    # Сервис сам обработает ошибки валидации и сохранения
    media = await media_service.save_media_file(
        db=db,
        file=file.file, # Передаем файловый объект
        filename=file.filename or "unknown", # Используем имя файла или заглушку
        content_type=file.content_type or "application/octet-stream" # Тип контента
    )
    # Возвращаем успешный ответ со схемой MediaCreateResult
    return MediaCreateResult(media_id=media.id)