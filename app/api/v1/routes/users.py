"""API роуты для работы с пользователями и их профилями."""

from fastapi import APIRouter, Path as FastApiPath, status

from app.api.v1.dependencies import CurrentUser, DBSession, UserSvc
from app.core.logging import log
from app.schemas import UserProfileResult

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfileResult,
    status_code=status.HTTP_200_OK,
    summary="Получение профиля текущего пользователя",
    description="Возвращает информацию о профиле аутентифицированного пользователя, включая списки подписчиков и подписок.",
)
async def get_my_profile(
        current_user: CurrentUser,
        db: DBSession,
        user_service: UserSvc,
) -> UserProfileResult:
    """
    Возвращает профиль текущего пользователя.

    Включает списки подписчиков и подписок.

    Args:
        current_user (CurrentUser): Аутентифицированный пользователь.
        db (DBSession): Сессия БД.
        user_service (UserSvc): Экземпляр сервиса `UserService`.

    Returns:
        UserProfileResult: Профиль пользователя.
    """
    log.info(f"Запрос профиля для текущего пользователя ID {current_user.id}")
    profile = await user_service.get_user_profile(db=db, user_id=current_user.id)
    return UserProfileResult(user=profile)


@router.get(
    "/{user_id}",
    response_model=UserProfileResult,
    status_code=status.HTTP_200_OK,
    summary="Получение профиля пользователя по ID",
    description="Возвращает информацию о профиле указанного пользователя, включая списки подписчиков и подписок.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"},
    }
)
async def get_user_profile_by_id(
        db: DBSession,
        user_service: UserSvc,
        user_id: int = FastApiPath(..., description="ID пользователя для просмотра профиля", gt=0),
) -> UserProfileResult:
    """
    Возвращает профиль пользователя по указанному ID.

    Включает списки подписчиков и подписок. Доступен без аутентификации.

    Args:
        db (DBSession): Сессия БД.
        user_service (UserSvc): Экземпляр сервиса `UserService`.
        user_id (int): ID пользователя.

    Returns:
        UserProfileResult: Профиль пользователя.

    Raises:
        NotFoundError: Если пользователь с указанным ID не найден.
    """
    log.info(f"Запрос профиля для пользователя ID {user_id}")
    profile = await user_service.get_user_profile(db=db, user_id=user_id)
    return UserProfileResult(user=profile)
