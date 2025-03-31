from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_api_key(self, api_key: str) -> User | None:
        """Находит пользователя по API-ключу.

        Args:
            api_key: Ключ для поиска (любая строка)

        Returns:
            User | None: Найденный пользователь или None
        """
        result = await self.session.execute(select(User).filter_by(api_key=api_key))
        return result.scalar_one_or_none()
