"""Сервисный слой для работы с профилями пользователей."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.follow import FollowRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserDetailResponse, UserProfileResponse


class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.follow_repo = FollowRepository(db)

    async def get_user_profile(
            self,
            current_user_id: int,
            target_user_id: int
    ) -> UserProfileResponse:
        """Получить основной профиль пользователя.

        Args:
            current_user_id: ID текущего пользователя
            target_user_id: ID целевого пользователя

        Returns:
            UserProfileResponse: Основная информация о профиле
        """
        user = await self.user_repo.get_by_id(target_user_id)
        if not user:
            raise ValueError("Пользователь не найден")

        followers, following = await self.follow_repo.get_follow_stats(target_user_id)
        is_following = await self.follow_repo.is_following(current_user_id, target_user_id)

        return UserProfileResponse(
            id=user.id,
            name=user.name,
            followers_count=followers,
            following_count=following,
            is_following=is_following
        )

    async def get_current_user_profile(
            self,
            user_id: int
    ) -> UserDetailResponse:
        """Получить полный профиль текущего пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            UserDetailResponse: Детализированная информация о профиле
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Пользователь не найден")

        stats = await self.follow_repo.get_user_follow_stats(user_id)

        return UserDetailResponse(
            id=user.id,
            name=user.name,
            followers_count=len(stats.followers),
            following_count=len(stats.following),
            is_following=False,  # Для своего профиля всегда False
            followers=stats.followers,
            following=stats.following
        )
