from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core.database import get_db
from app.repositories.user_repository import UserRepository

# Определяем заголовок для авторизации
API_KEY_HEADER = APIKeyHeader(name="api-key", auto_error=False)

# get_db_dep = Depends(get_db)


async def get_current_user(
        api_key: str = Security(API_KEY_HEADER),
        db: AsyncSession = Depends(get_db)
):
    """Аутентификация пользователя по api-key."""
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )

    # Проверяем, существует ли пользователь с данным API-ключом
    user = await UserRepository.get_by_api_key(session=db, api_key=api_key)

    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return user


# ds
# def get_current_user(api_key: str = Header(..., alias="api-key")) -> User:
#     user = UserRepository.get_by_api_key(api_key)
#     if not user:
#         raise HTTPException(status_code=403, detail="Invalid API key")
#     return user