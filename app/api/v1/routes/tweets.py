"""API роуты для работы с твитами (создание, удаление, лента)."""

from fastapi import APIRouter, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.services import tweet_service  # Импортируем сервис твитов
from app.schemas import (TweetActionResult, TweetCreateRequest,
                         TweetCreateResult, TweetFeedResult)

# Создаем роутер для твитов
router = APIRouter(prefix="/tweets", tags=["Tweets"])


@router.post(
    "",  # POST /api_old/v1/tweets
    response_model=TweetCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового твита",
    description="Позволяет аутентифицированному пользователю опубликовать новый твит, опционально прикрепив медиа.",
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
        db=db, current_user=current_user, tweet_data=tweet_in
    )
    return TweetCreateResult(tweet_id=tweet.id)


@router.get(
    "",  # GET /api_old/v1/tweets
    response_model=TweetFeedResult,
    status_code=status.HTTP_200_OK,
    summary="Получение ленты твитов",
    description="Возвращает ленту твитов от пользователей, на которых подписан текущий пользователь, и его собственные твиты, отсортированные по популярности.",
)
async def get_tweets_feed(
        current_user: CurrentUser,  # Аутентификация обязательна
        db: DBSession,
        # Можно добавить параметры пагинации (limit, offset), если нужно
        # limit: int = Query(50, gt=0, le=100),
        # offset: int = Query(0, ge=0),
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
    "/{tweet_id}",  # DELETE /api_old/v1/tweets/{tweet_id}
    response_model=TweetActionResult,
    status_code=status.HTTP_200_OK,  # Или 204 No Content, но тогда response_model не нужен
    summary="Удаление твита",
    description="Позволяет автору твита удалить его.",
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
    await tweet_service.delete_tweet(db=db, current_user=current_user, tweet_id=tweet_id)
    return TweetActionResult()  # result=True по умолчанию
