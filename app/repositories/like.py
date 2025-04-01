"""Репозиторий для работы с лайками в БД."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.like import Like


class LikeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_likes_count(self, tweet_id: int) -> int:
        """Возвращает количество лайков твита.

        Args:
            tweet_id: ID твита

        Returns:
            int: Количество лайков
        """
        result = await self.session.execute(
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
        result = await self.session.execute(
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
        self.session.add(like)
        await self.session.commit()

    async def remove_like(self, user_id: int, tweet_id: int):
        """Удаляет лайк с твита.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Raises:
            ValueError: Если лайк не найден
        """
        result = await self.session.execute(
            select(Like)
            .where(Like.user_id == user_id)
            .where(Like.tweet_id == tweet_id)
        )
        like = result.scalar_one_or_none()

        if not like:
            raise ValueError("Лайк не найден")

        await self.session.delete(like)
        await self.session.commit()


# v2
# """Репозиторий для работы с лайками."""
#
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.models.like import Like
#
#
# class LikeRepository:
#     def __init__(self, session: AsyncSession):
#         self.session = session
#
#     async def toggle_like(self, user_id: int, tweet_id: int) -> bool:
#         """Переключает лайк (ставит/убирает)."""
#         like = await self.session.execute(
#             select(Like)
#             .where(Like.user_id == user_id)
#             .where(Like.tweet_id == tweet_id)
#         )
#         like = like.scalar_one_or_none()
#
#         if like:
#             await self.session.delete(like)
#             await self.session.commit()
#             return False
#         else:
#             new_like = Like(user_id=user_id, tweet_id=tweet_id)
#             self.session.add(new_like)
#             await self.session.commit()
#             return True