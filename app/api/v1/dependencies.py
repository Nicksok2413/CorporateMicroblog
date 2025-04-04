"""Зависимости FastAPI для API версии v1."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from app.core.logging import log
from app.models.user import User
from app.repositories import user_repo

# --- Типизация для инъекции зависимостей ---

# Сессия базы данных
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# --- Зависимость для получения текущего пользователя ---

async def get_current_user(
        db: DBSession,
        api_key: Annotated[str | None, Header(description="Ключ API для аутентификации пользователя.")] = None
) -> User:
    """
    Зависимость для получения текущего пользователя на основе API ключа.

    Проверяет наличие заголовка `api-key` и ищет пользователя в базе данных.

    Args:
        db (AsyncSession): Сессия базы данных, предоставляемая зависимостью `get_db_session`.
        api_key (str | None): Значение заголовка `api-key` из запроса.

    Returns:
        User: Объект аутентифицированного пользователя.

    Raises:
        AuthenticationRequiredError(401): Если заголовок `api-key` отсутствует.
        PermissionDeniedError(403): Если пользователь с таким `api-key` не найден в базе данных.
    """
    if api_key is None:
        log.warning("Запрос без API ключа.")
        # Используем кастомное исключение для 401
        raise AuthenticationRequiredError(
            detail="Отсутствует заголовок api-key.",
            # Добавляем заголовок WWW-Authenticate через extra в исключении
            extra={"headers": {"WWW-Authenticate": "Header"}}
        )

    log.debug(f"Попытка аутентификации по API ключу: {api_key[:4]}...{api_key[-4:]}")
    user = await user_repo.get_by_api_key(db=db, api_key=api_key)

    if user is None:
        log.warning(f"Недействительный API ключ: {api_key[:4]}...{api_key[-4:]}")
        # Используем кастомное исключение для 403
        raise PermissionDeniedError(detail="Недействительный API ключ.")

    log.info(f"Пользователь ID {user.id} ({user.name}) аутентифицирован.")
    return user


# --- Типизация для инъекции текущего пользователя ---
CurrentUser = Annotated[User, Depends(get_current_user)]
