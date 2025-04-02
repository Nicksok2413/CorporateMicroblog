"""API роуты для лайков твитов."""

from fastapi import APIRouter, Depends, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.schemas import TweetActionResult  # Общий ответ для лайка/анлайка
from app.services import tweet_service  # Логика лайков находится в TweetService

# Роутер для лайков
# Префикс будет добавлен при подключении роутера,
# поэтому здесь указываем только относительный путь от /tweets/{tweet_id}
router = APIRouter(tags=["Likes"])


@router.post(
    # Полный путь будет /api/v1/tweets/{tweet_id}/likes
    "/tweets/{tweet_id}/likes",
    response_model=TweetActionResult,
    status_code=status.HTTP_201_CREATED,  # 201 или 200? 201 если ресурс 'лайк' создается
    summary="Поставить лайк твиту",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_409_CONFLICT: {"description": "Твит уже лайкнут этим пользователем"},
    }
)
async def like_a_tweet(
        current_user: CurrentUser = Depends(),
        db: DBSession = Depends(),
        tweet_id: int = FastApiPath(..., description="ID твита для лайка", gt=0),
):
    """
    Ставит лайк на указанный твит от имени текущего пользователя.

    Args:
        current_user: Пользователь, ставящий лайк.
        db: Сессия БД.
        tweet_id: ID твита для лайка.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если твит не найден.
        ConflictError: Если пользователь уже лайкнул этот твит.
        BadRequestError: При ошибке сохранения лайка.
    """
    log.info(f"Запрос на лайк твита ID {tweet_id} от пользователя ID {current_user.id}")
    await tweet_service.like_tweet(db=db, tweet_id=tweet_id, current_user=current_user)
    return TweetActionResult()


@router.delete(
    # Полный путь будет /api/v1/tweets/{tweet_id}/likes
    "/tweets/{tweet_id}/likes",
    response_model=TweetActionResult,
    status_code=status.HTTP_200_OK,
    summary="Убрать лайк с твита",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден или лайк отсутствует"},
    }
)
async def unlike_a_tweet(
        current_user: CurrentUser = Depends(),
        db: DBSession = Depends(),
        tweet_id: int = FastApiPath(..., gt=0, description="ID твита для снятия лайка"),
):
    """
    Убирает лайк с указанного твита от имени текущего пользователя.

    Args:
        current_user: Пользователь, убирающий лайк.
        db: Сессия БД.
        tweet_id: ID твита для снятия лайка.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если лайк для удаления не найден.
        BadRequestError: При ошибке удаления лайка.
    """
    log.info(f"Запрос на снятие лайка с твита ID {tweet_id} от пользователя ID {current_user.id}")
    await tweet_service.unlike_tweet(db=db, tweet_id=tweet_id, current_user=current_user)
    return TweetActionResult()
