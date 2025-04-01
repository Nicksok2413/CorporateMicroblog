"""Репозиторий для работы с подписками в БД."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.user import User


class FollowRepository:
    def __init__(self, sessiob: AsyncSession):
        self.session = sessiob

    async def get_follow_stats(self, user_id: int) -> tuple[int, int]:
        """Возвращает статистику подписок пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            tuple: (followers_count, following_count)
        """
        followers = await self.session.execute(
            select(func.count())
            .where(Follow.followed_id == user_id)
        )
        following = await self.session.execute(
            select(func.count())
            .where(Follow.follower_id == user_id)
        )
        return followers.scalar_one(), following.scalar_one()

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Проверяет наличие подписки.

        Args:
            follower_id: ID подписчика
            followed_id: ID целевого пользователя

        Returns:
            bool: True если подписка существует
        """
        result = await self.session.execute(
            select(Follow)
            .where(Follow.follower_id == follower_id)
            .where(Follow.followed_id == followed_id)
        )
        return result.scalar_one_or_none() is not None

    async def add_follow(self, follower_id: int, followed_id: int):
        """Добавляет подписку.

        Args:
            follower_id: ID подписчика
            followed_id: ID целевого пользователя

        Raises:
            ValueError: При попытке подписаться на себя
                      или если подписка уже существует
        """
        if follower_id == followed_id:
            raise ValueError("Нельзя подписаться на самого себя")

        if await self.is_following(follower_id, followed_id):
            raise ValueError("Подписка уже существует")

        follow = Follow(follower_id=follower_id, followed_id=followed_id)
        self.session.add(follow)
        await self.session.commit()

    async def remove_follow(self, follower_id: int, followed_id: int):
        """Удаляет подписку.

        Args:
            follower_id: ID подписчика
            followed_id: ID целевого пользователя

        Raises:
            ValueError: Если подписка не найдена
        """
        result = await self.session.execute(
            select(Follow)
            .where(Follow.follower_id == follower_id)
            .where(Follow.followed_id == followed_id)
        )
        follow = result.scalar_one_or_none()

        if not follow:
            raise ValueError("Подписка не найдена")

        await self.session.delete(follow)
        await self.session.commit()

    async def get_followers_list(self, user_id: int) -> list[tuple[int, str]]:
        """Возвращает список подписчиков.

        Args:
            user_id: ID пользователя

        Returns:
            list: Список кортежей (id, name)
        """
        result = await self.session.execute(
            select(User.id, User.name)
            .join(Follow, User.id == Follow.follower_id)
            .where(Follow.followed_id == user_id)
        )
        return result.all()

    async def get_following_list(self, user_id: int) -> list[tuple[int, str]]:
        """Возвращает список подписок.

        Args:
            user_id: ID пользователя

        Returns:
            list: Список кортежей (id, name)
        """
        result = await self.session.execute(
            select(User.id, User.name)
            .join(Follow, User.id == Follow.followed_id)
            .where(Follow.follower_id == user_id)
        )
        return result.all()
