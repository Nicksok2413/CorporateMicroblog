"""API роуты для подписок пользователей."""

from fastapi import APIRouter, Path, status

from app.api.v1.dependencies import CurrentUser, DBSession, FollowSvc
from app.core.logging import log
from app.schemas.base import ResultTrue

router = APIRouter(tags=["Follows"])


@router.post(
    "/users/{user_id}/follow",
    response_model=ResultTrue,
    status_code=status.HTTP_201_CREATED,
    summary="Подписаться на пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя подписаться на себя"},
        status.HTTP_409_CONFLICT: {"description": "Уже подписаны"},
    }
)
async def follow_a_user(
        db: DBSession,
        current_user: CurrentUser,
        follow_service: FollowSvc,
        user_id: int = Path(..., description="ID пользователя, на которого нужно подписаться", gt=0),
) -> ResultTrue:
    """
    Создает подписку текущего пользователя на указанного пользователя.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        follow_service (FollowSvc): Экземпляр сервиса `FollowService`.
        user_id (int): ID пользователя, на которого подписываются.

    Returns:
        ResultTrue: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если целевой пользователь не найден.
        PermissionDeniedError: Если пользователь пытается подписаться на себя.
        ConflictError: Если подписка уже существует.
        BadRequestError: При ошибке сохранения.
    """
    log.info(f"Запрос на подписку от пользователя ID {current_user.id} на пользователя ID {user_id}")
    await follow_service.follow_user(db=db, current_user=current_user, user_to_follow_id=user_id)
    return ResultTrue()


@router.delete(
    "/users/{user_id}/follow",
    response_model=ResultTrue,
    status_code=status.HTTP_200_OK,
    summary="Отписаться от пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден или подписка отсутствует"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя отписаться от себя"},
    }
)
async def unfollow_a_user(
        db: DBSession,
        current_user: CurrentUser,
        follow_service: FollowSvc,
        user_id: int = Path(..., description="ID пользователя, от которого нужно отписаться", gt=0),
) -> ResultTrue:
    """
    Удаляет подписку текущего пользователя от указанного пользователя.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        follow_service (FollowSvc): Экземпляр сервиса `FollowService`.
        user_id (int): ID пользователя, от которого отписываются.

    Returns:
        ResultTrue: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если целевой пользователь не найден или подписка отсутствовала.
        PermissionDeniedError: Если пользователь пытается отписаться от себя.
        BadRequestError: При ошибке удаления.
    """
    log.info(f"Запрос на отписку от пользователя ID {user_id} от пользователя ID {current_user.id}")
    await follow_service.unfollow_user(db=db, current_user=current_user, user_to_unfollow_id=user_id)
    return ResultTrue()
