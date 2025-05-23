"""Зависимости FastAPI для API версии v1."""

import hashlib
from typing import Annotated, Optional

from fastapi import Depends, Header
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from src.core.logging import log
from src.models import Media, Tweet, User
from src.repositories import (
    FollowRepository,
    LikeRepository,
    MediaRepository,
    TweetRepository,
    UserRepository,
)
from src.services import (
    FollowService,
    LikeService,
    MediaService,
    TweetService,
    UserService,
)

# --- Типизация для инъекции зависимостей ---

# Сессия базы данных
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# --- Фабрики Репозиториев ---


def get_follow_repository() -> FollowRepository:
    # FollowRepository не зависит от модели в конструкторе
    return FollowRepository()


def get_like_repository() -> LikeRepository:
    # LikeRepository не зависит от модели в конструкторе
    return LikeRepository()


def get_media_repository() -> MediaRepository:
    return MediaRepository(Media)


def get_tweet_repository() -> TweetRepository:
    return TweetRepository(Tweet)


def get_user_repository() -> UserRepository:
    return UserRepository(User)


# Типизация для репозиториев
FollowRepo = Annotated[FollowRepository, Depends(get_follow_repository)]
LikeRepo = Annotated[LikeRepository, Depends(get_like_repository)]
MediaRepo = Annotated[MediaRepository, Depends(get_media_repository)]
TweetRepo = Annotated[TweetRepository, Depends(get_tweet_repository)]
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]


# --- Фабрики Сервисов ---


# FollowService зависит от FollowRepo и UserRepo
def get_follow_service(repo: FollowRepo, user_repo: UserRepo) -> FollowService:
    return FollowService(repo=repo, user_repo=user_repo)


# LikeService зависит от LikeRepo и TweetRepo
def get_like_service(repo: LikeRepo, tweet_repo: TweetRepo) -> LikeService:
    return LikeService(repo=repo, tweet_repo=tweet_repo)


# MediaService зависит только от MediaRepo
def get_media_service(repo: MediaRepo) -> MediaService:
    return MediaService(repo=repo)


# TweetService зависит от многих репозиториев и MediaService
def get_tweet_service(
    repo: TweetRepo,
    follow_repo: FollowRepo,
    media_repo: MediaRepo,
    media_svc: Annotated[
        MediaService, Depends(get_media_service)
    ],  # Зависит от другого сервиса
) -> TweetService:
    return TweetService(
        repo=repo,
        follow_repo=follow_repo,
        media_repo=media_repo,
        media_service=media_svc,
    )


# UserService зависит от UserRepo и FollowRepo
def get_user_service(repo: UserRepo, follow_repo: FollowRepo) -> UserService:
    return UserService(repo=repo, follow_repo=follow_repo)


# Типизация для сервисов
FollowSvc = Annotated[FollowService, Depends(get_follow_service)]
LikeSvc = Annotated[LikeService, Depends(get_like_service)]
MediaSvc = Annotated[MediaService, Depends(get_media_service)]
TweetSvc = Annotated[TweetService, Depends(get_tweet_service)]
UserSvc = Annotated[UserService, Depends(get_user_service)]

# --- Зависимость для получения текущего пользователя ---


# Настройка Хеширования
pwd_context = CryptContext(schemes=["argon2"])


async def get_current_user(
    db: DBSession,
    user_repo: UserRepo,
    api_key: Annotated[
        Optional[str], Header(description="Ключ API для аутентификации пользователя.")
    ] = None,
) -> User:
    """
    Зависимость для получения текущего пользователя на основе хешированного API ключа.

    Проверяет наличие заголовка `api-key`, ищет пользователя по SHA256 хешу
    и верифицирует ключ с использованием Argon2.

    Args:
        db (AsyncSession): Сессия БД.
        user_repo (UserRepo): Экземпляр репозитория пользователей.
        api_key (Optional[str]): Значение заголовка `api-key` из запроса.

    Returns:
        User: Объект аутентифицированного пользователя.

    Raises:
        AuthenticationRequiredError(401): Если заголовок `api-key` отсутствует.
        PermissionDeniedError(403): Если пользователь с таким `api-key` не найден в БД.
    """
    if api_key is None:
        log.warning("Запрос без API ключа.")
        raise AuthenticationRequiredError(
            detail="Отсутствует заголовок api-key.",
            extra={"headers": {"WWW-Authenticate": "Header"}},
        )

    log.debug(f"Попытка аутентификации по API ключу: {api_key}")

    # 1. Вычисляем быстрый хеш от присланного ключа
    try:
        sha256_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    except Exception as exc:
        # Может случиться при странных входных данных
        log.error(f"Ошибка вычисления SHA256 для API ключа: {exc}")
        raise PermissionDeniedError(detail="Ошибка обработки ключа.")

    # 2. Ищем пользователя по быстрому хешу
    user = await user_repo.get_by_sha256(db=db, sha256_hash=sha256_hash)

    if user is None:
        # Пользователь с таким быстрым хешем не найден
        log.warning("Недействительный API ключ: SHA256 не найден.")
        raise PermissionDeniedError(detail="Недействительный API ключ.")

    # 3. Проверяем основной хеш с помощью passlib
    is_valid = pwd_context.verify(api_key, user.api_key_hash)

    if not is_valid:
        log.warning(f"Недействительный API ключ для user ID {user.id}: хеш не совпал.")
        raise PermissionDeniedError(detail="Недействительный API ключ.")

    # 4. Если все проверки пройдены
    log.info(f"Пользователь ID {user.id} ({user.name}) аутентифицирован.")
    return user


# --- Типизация для инъекции текущего пользователя ---
CurrentUser = Annotated[User, Depends(get_current_user)]
