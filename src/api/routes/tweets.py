"""API роуты для работы с твитами (создание, удаление, лайки, лента)."""

from fastapi import APIRouter, Path, status

from src.api.dependencies import CurrentUser, DBSession, LikeSvc, TweetSvc
from src.core.logging import log
from src.schemas.tweet import (TweetActionResult, TweetCreateRequest,
                               TweetCreateResult, TweetFeedResult)

router = APIRouter(prefix="/tweets", tags=["Tweets"])


@router.get(
    "",
    response_model=TweetFeedResult,
    status_code=status.HTTP_200_OK,
    summary="Получение ленты твитов",
    description="Возвращает ленту твитов от пользователей, на которых подписан текущий пользователь, и его собственные твиты, отсортированные по популярности.",
)
async def get_tweets_feed(
        db: DBSession,
        current_user: CurrentUser,
        tweet_service: TweetSvc,
) -> TweetFeedResult:
    """
    Возвращает ленту твитов для текущего пользователя.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        tweet_service (TweetSvc): Экземпляр сервиса `TweetService`.

    Returns:
        TweetFeedResult: Лента твитов.
    """
    log.info(f"Запрос ленты твитов для пользователя ID {current_user.id}")
    feed = await tweet_service.get_tweet_feed(db=db, current_user=current_user)
    return feed  # pragma: no cover


@router.post(
    "",
    response_model=TweetCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового твита",
    description="Позволяет аутентифицированному пользователю опубликовать новый твит, опционально прикрепив медиа.",
)
async def create_tweet(
        db: DBSession,
        current_user: CurrentUser,
        tweet_service: TweetSvc,
        tweet_in: TweetCreateRequest,
) -> TweetCreateResult:
    """
    Создает новый твит для текущего пользователя.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        tweet_service (TweetSvc): Экземпляр сервиса `TweetService`.
        tweet_in (TweetCreateRequest): Данные для создания твита.

    Returns:
        TweetCreateResult: Результат с ID созданного твита.

    Raises:
        NotFoundError: Если указанный media_id не найден (обрабатывается).
        BadRequestError: При ошибке сохранения в БД (обрабатывается).
    """
    log.info(f"Запрос на создание твита от пользователя ID {current_user.id}")
    tweet = await tweet_service.create_tweet(
        db=db, current_user=current_user, tweet_data=tweet_in
    )
    return TweetCreateResult(tweet_id=tweet.id)


@router.delete(
    "/{tweet_id}",
    response_model=TweetActionResult,
    status_code=status.HTTP_200_OK,
    summary="Удаление твита",
    description="Позволяет автору твита удалить его.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Недостаточно прав для удаления"},
    }
)
async def delete_tweet(
        db: DBSession,
        current_user: CurrentUser,
        tweet_service: TweetSvc,
        tweet_id: int = Path(..., description="ID твита для удаления", gt=0),
) -> TweetActionResult:
    """
    Удаляет твит по его ID.

    Доступно только автору твита.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        tweet_service (TweetSvc): Экземпляр сервиса `TweetService`.
        tweet_id (int): ID твита для удаления.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если твит не найден.
        PermissionDeniedError: Если пользователь не автор твита.
        BadRequestError: При ошибке удаления из БД.
    """
    log.info(f"Запрос на удаление твита ID {tweet_id} от пользователя ID {current_user.id}")
    await tweet_service.delete_tweet(db=db, current_user=current_user, tweet_id=tweet_id)
    return TweetActionResult()


@router.post(
    "/{tweet_id}/likes",
    response_model=TweetActionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Поставить лайк твиту",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_409_CONFLICT: {"description": "Твит уже лайкнут"},
    }
)
async def like_tweet(
        db: DBSession,
        current_user: CurrentUser,
        like_service: LikeSvc,
        tweet_id: int = Path(..., description="ID твита для лайка", gt=0),
) -> TweetActionResult:
    """
    Ставит лайк на указанный твит от имени текущего пользователя.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
        like_service (LikeSvc): Экземпляр сервиса `LikeService`.
        tweet_id (int): ID твита для лайка.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если твит не найден.
        BadRequestError: При ошибке сохранения лайка.
    """
    log.info(f"Запрос на лайк твита ID {tweet_id} от пользователя ID {current_user.id}")
    await like_service.like_tweet(db=db, current_user=current_user, tweet_id=tweet_id)
    return TweetActionResult()


@router.delete(
    "/{tweet_id}/likes",
    response_model=TweetActionResult,
    status_code=status.HTTP_200_OK,
    summary="Убрать лайк с твита",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Лайк не найден"},
    }
)
async def unlike_tweet(
        db: DBSession,
        current_user: CurrentUser,
        like_service: LikeSvc,
        tweet_id: int = Path(..., gt=0, description="ID твита для снятия лайка"),
) -> TweetActionResult:
    """
    Убирает лайк с указанного твита от имени текущего пользователя.

    Args:
        db (AsyncSession): Сессия БД.
        current_user (CurrentUser): Аутентифицированный пользователь.
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
