"""API роуты для подписок пользователей."""

from fastapi import APIRouter, Depends, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.schemas import ResultTrue  # Общий успешный ответ
from app.services import follow_service  # Сервис для подписок

# Роутер для подписок
router = APIRouter(tags=["Follows"])


@router.post(
    # Полный путь /api/v1/users/{user_id}/follow
    "/users/{user_id}/follow",
    response_model=ResultTrue,
    status_code=status.HTTP_201_CREATED,  # Ресурс 'подписка' создается
    summary="Подписаться на пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь для подписки не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя подписаться на себя"},
        status.HTTP_409_CONFLICT: {"description": "Вы уже подписаны на этого пользователя"},
    }
)
async def follow_a_user(
        current_user: CurrentUser,
        db: DBSession,
        user_id: int = FastApiPath(..., description="ID пользователя, на которого нужно подписаться", gt=0),
):
    """
    Создает подписку текущего пользователя на указанного пользователя.

    Args:
        current_user: Пользователь, выполняющий подписку.
        db: Сессия БД.
        user_id: ID пользователя, на которого подписываются.

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
    # Полный путь /api/v1/users/{user_id}/follow
    "/users/{user_id}/follow",
    response_model=ResultTrue,
    status_code=status.HTTP_200_OK,
    summary="Отписаться от пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден или вы не были на него подписаны"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя отписаться от себя"},
    }
)
async def unfollow_a_user(
        current_user: CurrentUser,
        db: DBSession,
        user_id: int = FastApiPath(..., description="ID пользователя, от которого нужно отписаться", gt=0),
):
    """
    Удаляет подписку текущего пользователя от указанного пользователя.

    Args:
        current_user: Пользователь, выполняющий отписку.
        db: Сессия БД.
        user_id: ID пользователя, от которого отписываются.

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
