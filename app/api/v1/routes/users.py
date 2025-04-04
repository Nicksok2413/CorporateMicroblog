"""API роуты для работы с пользователями и их профилями."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path as FastApiPath, status

from app.api.v1.dependencies import CurrentUser, DBSession, UserSvc, get_user_service
from app.core.logging import log
from app.services import UserService
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
):
    """
    Возвращает профиль текущего пользователя.

    Включает списки подписчиков и подписок.

    Args:
        current_user: Аутентифицированный пользователь.
        db: Сессия БД.

    Returns:
        UserProfileResult: Профиль пользователя.
    """
    log.info(f"Запрос профиля для текущего пользователя ID {current_user.id}")
    profile = await user_service.get_user_profile(db=db, user_id=current_user.id)
    # Возвращаем в формате { "result": true, "user": { ... } }
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
):
    """
    Возвращает профиль пользователя по указанному ID.

    Включает списки подписчиков и подписок. Доступен без аутентификации.

    Args:
        db: Сессия БД.
        user_id: ID пользователя.

    Returns:
        UserProfileResult: Профиль пользователя.

    Raises:
        NotFoundError: Если пользователь с указанным ID не найден.
    """
    log.info(f"Запрос профиля для пользователя ID {user_id}")
    profile = await user_service.get_user_profile(db=db, user_id=user_id)
    # Обработчик исключений поймает NotFoundError из сервиса
    return UserProfileResult(user=profile)
