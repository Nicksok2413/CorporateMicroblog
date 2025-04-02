"""API роуты для работы с твитами (создание, удаление, лента)."""

from fastapi import APIRouter, Depends, Path as FastApiPath, status

# Импортируем зависимости, сервисы и схемы
from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.logging import log
from app.schemas import (TweetActionResult, TweetCreateRequest,
                         TweetCreateResult, TweetFeedResult)
from app.services import tweet_service

# Роутер для твитов
router = APIRouter(tags=["Tweets"])


@router.post(
    "/tweets",
    response_model=TweetCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового твита",
    description="Позволяет аутентифицированному пользователю опубликовать новый твит, опционально прикрепив медиа.",
)
async def create_new_tweet(
    tweet_in: TweetCreateRequest, # Данные твита из тела запроса
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Создает новый твит.

    Args:
        tweet_in: Данные нового твита.
        current_user: Текущий аутентифицированный пользователь.
        db: Сессия базы данных.

    Returns:
        TweetCreateResult: Результат с ID созданного твита.

    Raises:
        NotFoundError: Если указанный media_id не найден.
        BadRequestError: При ошибке сохранения в БД.
    """
    log.info(f"Пользователь ID {current_user.id} создает новый твит.")
    tweet = await tweet_service.create_tweet(
        db=db, tweet_data=tweet_in, current_user=current_user
    )
    return TweetCreateResult(tweet_id=tweet.id)


@router.delete(
    "/tweets/{tweet_id}",
    response_model=TweetActionResult, # Возвращает { "result": true }
    status_code=status.HTTP_200_OK,
    summary="Удаление твита",
    description="Позволяет автору твита удалить его.",
    responses={ # Дополнительные возможные ответы для Swagger
        status.HTTP_404_NOT_FOUND: {"description": "Твит не найден"},
        status.HTTP_403_FORBIDDEN: {"description": "Недостаточно прав для удаления"},
    }
)
async def delete_existing_tweet(
    # Path параметр с валидацией (должен быть > 0)
    tweet_id: int = FastApiPath(..., gt=0, description="ID твита для удаления"),
    current_user: CurrentUser = Depends(), # Используем Depends() как альтернативу аннотации
    db: DBSession = Depends(),
):
    """
    Удаляет твит по его ID.

    Args:
        tweet_id: ID твита в пути URL.
        current_user: Текущий аутентифицированный пользователь.
        db: Сессия базы данных.

    Returns:
        TweetActionResult: Стандартный успешный ответ.

    Raises:
        NotFoundError: Если твит не найден.
        PermissionDeniedError: Если пользователь пытается удалить чужой твит.
        BadRequestError: При ошибке удаления из БД.
    """
    log.info(f"Пользователь ID {current_user.id} удаляет твит ID {tweet_id}.")
    await tweet_service.delete_tweet(db=db, tweet_id=tweet_id, current_user=current_user)
    # Если сервис не вызвал исключение, удаление прошло успешно
    return TweetActionResult()


@router.get(
    "/tweets",
    response_model=TweetFeedResult,
    status_code=status.HTTP_200_OK,
    summary="Получение ленты твитов",
    description="Возвращает ленту твитов для аутентифицированного пользователя "
                "(твиты отслеживаемых пользователей и собственные), "
                "отсортированную по популярности.",
)
async def get_user_feed(
    current_user: CurrentUser,
    db: DBSession,
    # Можно добавить параметры пагинации (limit, offset), если нужно
    # limit: int = Query(50, gt=0, le=100),
    # offset: int = Query(0, ge=0),
):
    """
    Возвращает ленту твитов пользователя.

    Args:
        current_user: Текущий аутентифицированный пользователь.
        db: Сессия базы данных.

    Returns:
        TweetFeedResult: Лента твитов.
    """
    log.info(f"Запрос ленты твитов для пользователя ID {current_user.id}")
    feed_result = await tweet_service.get_tweet_feed(db=db, current_user=current_user)
    return feed_result