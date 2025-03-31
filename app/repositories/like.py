"""Репозиторий для работы с лайками в БД."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.like import Like


class LikeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_likes_count(self, tweet_id: int) -> int:
        """Возвращает количество лайков твита.

        Args:
            tweet_id: ID твита

        Returns:
            int: Количество лайков
        """
        result = await self.db.execute(
            select(func.count())
            .where(Like.tweet_id == tweet_id)
        )
        return result.scalar_one()

    async def is_liked(self, user_id: int, tweet_id: int) -> bool:
        """Проверяет, поставил ли пользователь лайк твиту.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Returns:
            bool: True если лайк существует
        """
        result = await self.db.execute(
            select(Like)
            .where(Like.user_id == user_id)
            .where(Like.tweet_id == tweet_id)
        )
        return result.scalar_one_or_none() is not None

    async def add_like(self, user_id: int, tweet_id: int):
        """Добавляет лайк твиту.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Raises:
            ValueError: Если лайк уже существует
        """
        if await self.is_liked(user_id, tweet_id):
            raise ValueError("Лайк уже поставлен")

        like = Like(user_id=user_id, tweet_id=tweet_id)
        self.db.add(like)
        await self.db.commit()

    async def remove_like(self, user_id: int, tweet_id: int):
        """Удаляет лайк с твита.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Raises:
            ValueError: Если лайк не найден
        """
        result = await self.db.execute(
            select(Like)
            .where(Like.user_id == user_id)
            .where(Like.tweet_id == tweet_id)
        )
        like = result.scalar_one_or_none()

        if not like:
            raise ValueError("Лайк не найден")

        await self.db.delete(like)
        await self.db.commit()
