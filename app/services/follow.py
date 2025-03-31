"""Сервисный слой для работы с подписками."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.follow import FollowRepository
from app.schemas.follow import FollowResponse, UserFollow, UserFollowStats


class FollowService:
    def __init__(self, db: AsyncSession):
        self.repo = FollowRepository(db)

    async def follow_user(
            self,
            follower_id: int,
            followed_id: int
    ) -> FollowResponse:
        """Подписаться на пользователя.

        Args:
            follower_id: ID подписчика
            followed_id: ID целевого пользователя

        Returns:
            FollowResponse: Статистика подписок

        Raises:
            ValueError: При ошибках валидации
        """
        await self.repo.add_follow(follower_id, followed_id)
        return await self._build_response(follower_id, followed_id)

    async def unfollow_user(
            self,
            follower_id: int,
            followed_id: int
    ) -> FollowResponse:
        """Отписаться от пользователя.

        Args:
            follower_id: ID подписчика
            followed_id: ID целевого пользователя

        Returns:
            FollowResponse: Статистика подписок

        Raises:
            ValueError: При ошибках валидации
        """
        await self.repo.remove_follow(follower_id, followed_id)
        return await self._build_response(follower_id, followed_id)

    async def get_follow_stats(
            self,
            current_user_id: int,
            target_user_id: int
    ) -> FollowResponse:
        """Получить статистику подписок.

        Args:
            current_user_id: ID текущего пользователя
            target_user_id: ID целевого пользователя

        Returns:
            FollowResponse: Статистика подписок
        """
        return await self._build_response(current_user_id, target_user_id)

    async def get_user_follow_stats(
            self,
            user_id: int
    ) -> UserFollowStats:
        """Получить детальную статистику подписок.

        Args:
            user_id: ID пользователя

        Returns:
            UserFollowStats: Детализированная статистика
        """
        followers = await self.repo.get_followers_list(user_id)
        following = await self.repo.get_following_list(user_id)

        return UserFollowStats(
            followers=[UserFollow(id=f[0], name=f[1]) for f in followers],
            following=[UserFollow(id=f[0], name=f[1]) for f in following]
        )

    async def _build_response(
            self,
            current_user_id: int,
            target_user_id: int
    ) -> FollowResponse:
        """Формирует ответ со статистикой подписок.

        Args:
            current_user_id: ID текущего пользователя
            target_user_id: ID целевого пользователя

        Returns:
            FollowResponse: Информация о подписках
        """
        followers_count, following_count = await self.repo.get_follow_stats(target_user_id)
        is_following = await self.repo.is_following(current_user_id, target_user_id)

        return FollowResponse(
            user_id=target_user_id,
            followers_count=followers_count,
            following_count=following_count,
            is_following=is_following
        )
