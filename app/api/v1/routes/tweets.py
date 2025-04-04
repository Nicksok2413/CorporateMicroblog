"""API роуты для работы с твитами (создание, удаление, лента)."""

from fastapi import APIRouter, Depends, Path as FastApiPath, status

from app.api.v1.dependencies import CurrentUser, DBSession, TweetSvc, get_tweet_service
from app.core.logging import log
from app.services import TweetService
from app.schemas import (TweetActionResult, TweetCreateRequest,
                         TweetCreateResult, TweetFeedResult)

router = APIRouter(prefix="/tweets", tags=["Tweets"])


@router.post(
    "",
    response_model=TweetCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового твита",
    description="Позволяет аутентифицированному пользователю опубликовать новый твит, опционально прикрепив медиа.",
)
async def create_new_tweet(
        tweet_in: TweetCreateRequest,
        current_user: CurrentUser,
        db: DBSession,
        tweet_service: TweetSvc,
):
    """
    Создает новый твит для текущего пользователя.

    Args:
        tweet_in: Данные для создания твита.
        current_user: Аутентифицированный пользователь.
        db: Сессия БД.

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


@router.get(
    "",
    response_model=TweetFeedResult,
    status_code=status.HTTP_200_OK,
    summary="Получение ленты твитов",
    description="Возвращает ленту твитов от пользователей, на которых подписан текущий пользователь, и его собственные твиты, отсортированные по популярности.",
)
async def get_tweets_feed(
        current_user: CurrentUser,
        db: DBSession,
        tweet_service: TweetSvc,
):
    """
    Возвращает ленту твитов для текущего пользователя.

    Args:
        current_user: Аутентифицированный пользователь.
        db: Сессия БД.

    Returns:
        TweetFeedResult: Лента твитов.
    """
    log.info(f"Запрос ленты твитов для пользователя ID {current_user.id}")
    feed = await tweet_service.get_tweet_feed(db=db, current_user=current_user)
    return feed


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
async def delete_existing_tweet(
        current_user: CurrentUser,
        db: DBSession,
        tweet_service: TweetSvc,
        tweet_id: int = FastApiPath(..., description="ID твита для удаления", gt=0),
):
    """
    Удаляет твит по его ID.

    Доступно только автору твита.

    Args:
        current_user: Пользователь, выполняющий удаление.
        db: Сессия БД.
        tweet_id: ID твита для удаления.

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
