from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.user_repository import UserRepository

async def get_current_user(
    api_key: str = Header(..., alias="api-key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return user