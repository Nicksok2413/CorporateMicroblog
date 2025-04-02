"""API роуты для работы с пользователями (профили)."""

from fastapi import APIRouter, Depends, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.schemas import UserProfileResult # Схема ответа для профиля
from app.services import user_service # Сервис пользователей

# Роутер для пользователей
router = APIRouter(tags=["Users"])


@router.get(
    # Полный путь /api/v1/users/me
    "/users/me",
    response_model=UserProfileResult,
    status_code=status.HTTP_200_OK,
    summary="Получение профиля текущего пользователя",
    description="Возвращает информацию о профиле аутентифицированного пользователя, включая списки подписчиков и подписок.",
)
async def read_current_user_profile(
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Возвращает профиль текущего пользователя.

    Args:
        current_user: Текущий аутентифицированный пользователь.
        db: Сессия базы данных.

    Returns:
        UserProfileResult: Профиль пользователя.
    """
    log.info(f"Запрос профиля для текущего пользователя (ID {current_user.id})")
    # Сервис user_service уже содержит логику формирования профиля
    profile = await user_service.get_user_profile(db=db, user_id=current_user.id)
    return UserProfileResult(user=profile)


@router.get(
    # Полный путь /api/v1/users/{user_id}
    "/users/{user_id}",
    response_model=UserProfileResult,
    status_code=status.HTTP_200_OK,
    summary="Получение профиля пользователя по ID",
    description="Возвращает информацию о профиле указанного пользователя, включая списки подписчиков и подписок. "
                "Аутентификация для этого эндпоинта не требуется по ТЗ.",
     responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"},
    }
)
async def read_user_profile_by_id(
    user_id: int = FastApiPath(..., gt=0, description="ID пользователя для просмотра профиля"),
    db: DBSession = Depends(),
    # current_user: CurrentUser = Depends() # Аутентификация не требуется
):
    """
    Возвращает профиль пользователя по ID.

    Args:
        user_id: ID пользователя в пути URL.
        db: Сессия базы данных.

    Returns:
        UserProfileResult: Профиль пользователя.

    Raises:
        NotFoundError: Если пользователь не найден.
    """
    log.info(f"Запрос профиля для пользователя ID {user_id}")
    profile = await user_service.get_user_profile(db=db, user_id=user_id)
    return UserProfileResult(user=profile)