"""API роуты для работы с пользователями, их профилями и подписками."""

from fastapi import APIRouter, Path, status

from src.api.dependencies import CurrentUser, DBSession, FollowSvc, UserSvc
from src.core.logging import log
from src.schemas.base import ResultTrue
from src.schemas.user import UserProfileResult

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfileResult,
    status_code=status.HTTP_200_OK,
    summary="Получение профиля текущего пользователя",
    description="Возвращает информацию о профиле аутентифицированного пользователя, "
    "включая списки подписчиков и подписок.",
)
async def get_my_profile(
    db: DBSession,
    current_user: CurrentUser,
    user_service: UserSvc,
) -> UserProfileResult:
    """
    Возвращает профиль текущего пользователя.

    Включает списки подписчиков и подписок.

    Args:
        db (DBSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
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
    description="Возвращает информацию о профиле указанного пользователя, "
    "включая списки подписчиков и подписок.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"},
    },
)
async def get_user_profile_by_id(
    db: DBSession,
    user_service: UserSvc,
    user_id: int = Path(..., description="ID пользователя для просмотра профиля", gt=0),
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


@router.post(
    "/{user_id}/follow",
    response_model=ResultTrue,
    status_code=status.HTTP_201_CREATED,
    summary="Подписаться на пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя подписаться на себя"},
        status.HTTP_409_CONFLICT: {"description": "Уже подписаны"},
    },
)
async def follow_user(
    db: DBSession,
    current_user: CurrentUser,
    follow_service: FollowSvc,
    user_id: int = Path(
        ..., description="ID пользователя, на которого нужно подписаться", gt=0
    ),
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
    log.info(
        f"Запрос на подписку от пользователя ID {current_user.id} на пользователя ID {user_id}"
    )
    await follow_service.follow_user(
        db=db, current_user=current_user, user_to_follow_id=user_id
    )
    return ResultTrue()


@router.delete(
    "/{user_id}/follow",
    response_model=ResultTrue,
    status_code=status.HTTP_200_OK,
    summary="Отписаться от пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Пользователь не найден или подписка отсутствует"
        },
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя отписаться от себя"},
    },
)
async def unfollow_user(
    db: DBSession,
    current_user: CurrentUser,
    follow_service: FollowSvc,
    user_id: int = Path(
        ..., description="ID пользователя, от которого нужно отписаться", gt=0
    ),
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
    log.info(
        f"Запрос на отписку от пользователя ID {user_id} от пользователя ID {current_user.id}"
    )
    await follow_service.unfollow_user(
        db=db, current_user=current_user, user_to_unfollow_id=user_id
    )
    return ResultTrue()
