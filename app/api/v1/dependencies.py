"""Зависимости FastAPI для API v1."""

from typing import Annotated, Optional  # Используем Annotated для Depends и Header

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем сессию БД и репозиторий пользователей
from app.core.database import get_db_session
from app.core.exceptions import PermissionDeniedError  # Используем наше кастомное исключение
from app.core.logging import log
from app.models import User  # Импортируем модель User
from app.repositories import user_repo  # Импортируем репозиторий

# Определяем тип для инъекции сессии БД для краткости
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
        # Получаем значение заголовка api-key. Он опционален на уровне FastAPI,
        # но мы проверим его наличие вручную.
        # Используем alias из настроек, если он там задан, или строку напрямую.
        # from app.core.config import settings # Если API_KEY_HEADER в настройках
        # api_key: Annotated[Optional[str], Header(alias=settings.API_KEY_HEADER)] = None,
        db: DBSession,  # Инъекция сессии БД
        api_key: Annotated[Optional[str], Header(alias="api-key", description="Ключ API пользователя")] = None
) -> User:
    """
    Зависимость для получения текущего аутентифицированного пользователя.

    Проверяет наличие и валидность API ключа, переданного в заголовке 'api-key'.

    Args:
        db: Асинхронная сессия базы данных (инъектируется FastAPI).
        api_key: Значение заголовка 'api-key' (инъектируется FastAPI).

    Returns:
        User: Объект аутентифицированного пользователя.

    Raises:
        PermissionDeniedError: Если API ключ отсутствует или недействителен.
                               (Используем 403 Forbidden, как более подходящий для невалидного ключа,
                               хотя 401 Unauthorized тоже возможен, особенно при отсутствии ключа).
    """
    if api_key is None:
        log.warning("Запрос без API ключа.")
        # Статус 401 или 403? 401 обычно означает "не аутентифицирован",
        # 403 - "аутентифицирован, но не авторизован".
        # При отсутствии ключа 401 выглядит логичнее.
        # Используем HTTPException для статуса 401, т.к. PermissionDeniedError - это 403.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API ключ отсутствует в заголовке 'api-key'.",
            headers={"WWW-Authenticate": "Header"},  # Необязательный заголовок для 401
        )

    log.debug(f"Попытка аутентификации по API ключу: {api_key[:4]}...{api_key[-4:]}")
    user = await user_repo.get_by_api_key(db=db, api_key=api_key)

    if user is None:
        log.warning(f"Недействительный API ключ: {api_key[:4]}...{api_key[-4:]}")
        # Если ключ есть, но он неверный - используем 403 Forbidden (PermissionDeniedError)
        raise PermissionDeniedError(detail="Недействительный API ключ.")

    log.info(f"Пользователь ID {user.id} ({user.name}) аутентифицирован.")
    return user


# Определяем тип для инъекции текущего пользователя для краткости
CurrentUser = Annotated[User, Depends(get_current_user)]
