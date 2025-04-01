"""API роуты для работы с твитами."""

from fastapi import APIRouter, Depends, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.services import tweet_service  # Импортируем сервис твитов
from app.schemas import (TweetActionResult, TweetCreateRequest,
                         TweetCreateResult, TweetFeedResult)

# Создаем роутер для твитов
router = APIRouter(prefix="/tweets", tags=["Tweets"])


@router.post(
    "",  # POST /api/v1/tweets
    response_model=TweetCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового твита",
)
async def create_new_tweet(
        tweet_in: TweetCreateRequest,  # Данные из тела запроса (валидируются Pydantic)
        current_user: CurrentUser,  # Аутентифицированный пользователь
        db: DBSession,  # Сессия БД
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
        db=db, tweet_data=tweet_in, current_user=current_user
    )
    return TweetCreateResult(tweet_id=tweet.id)


@router.get(
    "",  # GET /api/v1/tweets
    response_model=TweetFeedResult,
    summary="Получение ленты твитов",
    description="Возвращает ленту твитов от пользователей, на которых подписан текущий пользователь, и его собственные твиты, отсортированные по популярности.",
)
async def get_tweets_feed(
        current_user: CurrentUser,  # Аутентификация обязательна
        db: DBSession,
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
    "/{tweet_id}",  # DELETE /api/v1/tweets/{tweet_id}
    response_model=TweetActionResult,
    summary="Удаление твита",
    status_code=status.HTTP_200_OK,  # Или 204 No Content, но тогда response_model не нужен
    responses={  # Документируем возможные ошибки
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Недостаточно прав для удаления"},
    }
)
async def delete_existing_tweet(
        current_user: CurrentUser,
        db: DBSession,
        tweet_id: int = FastApiPath(..., description="ID твита для удаления", gt=0),  # Валидация параметра пути
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
    await tweet_service.delete_tweet(db=db, tweet_id=tweet_id, current_user=current_user)
    return TweetActionResult()  # result=True по умолчанию


@router.post(
    "/{tweet_id}/likes",  # POST /api/v1/tweets/{tweet_id}/likes
    response_model=TweetActionResult,
    summary="Поставить лайк твиту",
    status_code=status.HTTP_201_CREATED,  # Лайк - это создание ресурса (связи)
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_409_CONFLICT: {"description": "Твит уже лайкнут"},
    }
)
async def like_existing_tweet(
        current_user: CurrentUser,
        db: DBSession,
        tweet_id: int = FastApiPath(..., description="ID твита для лайка", gt=0),
):
    """
    Позволяет текущему пользователю лайкнуть твит.

    Args:
        current_user: Пользователь, ставящий лайк.
        db: Сессия БД.
        tweet_id: ID твита для лайка.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если твит не найден.
        ConflictError: Если лайк уже существует.
        BadRequestError: При ошибке сохранения лайка.
    """
    log.info(f"Запрос на лайк твита ID {tweet_id} от пользователя ID {current_user.id}")
    await tweet_service.like_tweet(db=db, tweet_id=tweet_id, current_user=current_user)
    return TweetActionResult()


@router.delete(
    "/{tweet_id}/likes",  # DELETE /api/v1/tweets/{tweet_id}/likes
    response_model=TweetActionResult,
    summary="Убрать лайк с твита",
    status_code=status.HTTP_200_OK,  # Успешное удаление
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден или лайк отсутствует"},
    }
)
async def unlike_existing_tweet(
        current_user: CurrentUser,
        db: DBSession,
        tweet_id: int = FastApiPath(..., description="ID твита для снятия лайка", gt=0),
):
    """
    Позволяет текущему пользователю убрать лайк с твита.

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
