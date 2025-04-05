"""API роуты для лайков твитов."""

from fastapi import APIRouter, Path as FastApiPath, status

from app.api.v1.dependencies import CurrentUser, DBSession, LikeSvc
from app.core.logging import log
from app.schemas import TweetActionResult

router = APIRouter(tags=["Likes"])


@router.post(
    "/tweets/{tweet_id}/likes",
    response_model=TweetActionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Поставить лайк твиту",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_409_CONFLICT: {"description": "Твит уже лайкнут"},
    }
)
async def like_a_tweet(
        current_user: CurrentUser,
        db: DBSession,
        like_service: LikeSvc,
        tweet_id: int = FastApiPath(..., description="ID твита для лайка", gt=0),
) -> TweetActionResult:
    """
    Ставит лайк на указанный твит от имени текущего пользователя.

    Args:
        current_user (CurrentUser): Аутентифицированный пользователь.
        db (AsyncSession): Сессия БД.
        like_service (LikeSvc): Экземпляр сервиса `LikeService`.
        tweet_id (int): ID твита для лайка.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если твит не найден.
        ConflictError: Если пользователь уже лайкнул этот твит.
        BadRequestError: При ошибке сохранения лайка.
    """
    log.info(f"Запрос на лайк твита ID {tweet_id} от пользователя ID {current_user.id}")
    await like_service.like_tweet(db=db, current_user=current_user, tweet_id=tweet_id)
    return TweetActionResult()


@router.delete(
    "/tweets/{tweet_id}/likes",
    response_model=TweetActionResult,
    status_code=status.HTTP_200_OK,
    summary="Убрать лайк с твита",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Лайк не найден"},
    }
)
async def unlike_a_tweet(
        current_user: CurrentUser,
        db: DBSession,
        like_service: LikeSvc,
        tweet_id: int = FastApiPath(..., gt=0, description="ID твита для снятия лайка"),
) -> TweetActionResult:
    """
    Убирает лайк с указанного твита от имени текущего пользователя.

    Args:
        current_user (CurrentUser): Аутентифицированный пользователь.
        db (AsyncSession): Сессия БД.
        like_service (LikeSvc): Экземпляр сервиса `LikeService`.
        tweet_id (int): ID твита для снятия лайка.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если лайк для удаления не найден.
        BadRequestError: При ошибке удаления лайка.
    """
    log.info(f"Запрос на снятие лайка с твита ID {tweet_id} от пользователя ID {current_user.id}")
    await like_service.unlike_tweet(db=db, current_user=current_user, tweet_id=tweet_id)
    return TweetActionResult()
