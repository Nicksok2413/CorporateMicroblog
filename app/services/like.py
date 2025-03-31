"""Сервисный слой для работы с лайками."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.like import LikeRepository
from app.schemas.like import LikeResponse


class LikeService:
    def __init__(self, db: AsyncSession):
        self.repo = LikeRepository(db)

    async def like_tweet(
            self,
            user_id: int,
            tweet_id: int
    ) -> LikeResponse:
        """Поставить лайк твиту.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Returns:
            LikeResponse: Статус лайка

        Raises:
            ValueError: При ошибках валидации
        """
        await self.repo.add_like(user_id, tweet_id)
        return await self._build_response(user_id, tweet_id)

    async def unlike_tweet(
            self,
            user_id: int,
            tweet_id: int
    ) -> LikeResponse:
        """Убрать лайк с твита.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Returns:
            LikeResponse: Статус лайка

        Raises:
            ValueError: При ошибках валидации
        """
        await self.repo.remove_like(user_id, tweet_id)
        return await self._build_response(user_id, tweet_id)

    async def _build_response(
            self,
            user_id: int,
            tweet_id: int
    ) -> LikeResponse:
        """Формирует ответ с информацией о лайках.

        Args:
            user_id: ID пользователя
            tweet_id: ID твита

        Returns:
            LikeResponse: Информация о лайках
        """
        likes_count = await self.repo.get_likes_count(tweet_id)
        is_liked = await self.repo.is_liked(user_id, tweet_id)
        return LikeResponse(
            tweet_id=tweet_id,
            likes_count=likes_count,
            is_liked=is_liked
        )
