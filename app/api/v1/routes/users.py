"""API роуты для работы с пользователями и их профилями."""

from fastapi import APIRouter, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.services import user_service, follow_service  # Импортируем сервисы
from app.schemas import UserProfileResult, ResultTrue  # Импортируем схемы

# Создаем роутер для пользователей
router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",  # GET /api/v1/users/me
    response_model=UserProfileResult,
    summary="Получение профиля текущего пользователя",
)
async def get_my_profile(
        current_user: CurrentUser,  # Требует аутентификации
        db: DBSession,
):
    """
    Возвращает профиль текущего аутентифицированного пользователя.

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
    "/{user_id}",  # GET /api/v1/users/{user_id}
    response_model=UserProfileResult,
    summary="Получение профиля пользователя по ID",
    responses={  # Документируем возможные ошибки
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"},
    }
)
async def get_user_profile_by_id(
        # Аутентификация НЕ ТРЕБУЕТСЯ по ТЗ для этого эндпоинта
        db: DBSession,
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


@router.post(
    "/{user_id}/follow",  # POST /api/v1/users/{user_id}/follow
    response_model=ResultTrue,  # Возвращаем базовый успешный ответ
    summary="Подписаться на пользователя",
    status_code=status.HTTP_201_CREATED,  # Подписка - создание связи
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь для подписки не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя подписаться на себя"},
        status.HTTP_409_CONFLICT: {"description": "Уже подписан на этого пользователя"},
    }
)
async def follow_target_user(
        current_user: CurrentUser,  # Текущий пользователь подписывается
        db: DBSession,
        user_id: int = FastApiPath(..., description="ID пользователя, на которого нужно подписаться", gt=0),
):
    """
    Позволяет текущему пользователю подписаться на другого пользователя.

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
    await follow_service.follow_user(
        db=db, current_user=current_user, user_to_follow_id=user_id
    )
    return ResultTrue()


@router.delete(
    "/{user_id}/follow",  # DELETE /api/v1/users/{user_id}/follow
    response_model=ResultTrue,  # Возвращаем базовый успешный ответ
    summary="Отписаться от пользователя",
    status_code=status.HTTP_200_OK,  # Успешное удаление связи
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден или подписка отсутствует"},
        status.HTTP_403_FORBIDDEN: {"description": "Нельзя отписаться от себя"},
    }
)
async def unfollow_target_user(
        current_user: CurrentUser,  # Текущий пользователь отписывается
        db: DBSession,
        user_id: int = FastApiPath(..., description="ID пользователя, от которого нужно отписаться", gt=0),
):
    """
    Позволяет текущему пользователю отписаться от другого пользователя.

    Args:
        current_user: Пользователь, выполняющий отписку.
        db: Сессия БД.
        user_id: ID пользователя, от которого отписываются.

    Returns:
        ResultTrue: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если целевой пользователь или подписка не найдены.
        PermissionDeniedError: Если пользователь пытается отписаться от себя.
        BadRequestError: При ошибке удаления.
    """
    log.info(f"Запрос на отписку от пользователя ID {user_id} от пользователя ID {current_user.id}")
    await follow_service.unfollow_user(
        db=db, current_user=current_user, user_to_unfollow_id=user_id
    )
    return ResultTrue()
