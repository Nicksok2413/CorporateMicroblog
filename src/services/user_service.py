"""Сервис для работы с пользователями."""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import log
from src.models import Follow, User
from src.repositories import FollowRepository, UserRepository
from src.schemas.user import BaseUser, UserProfile
from src.services.base_service import BaseService


class UserService(BaseService[User, UserRepository]):
    """
    Сервис для бизнес-логики, связанной с пользователями.

    Включает получение профилей, управление подписками (через FollowService).
    """

    def __init__(self, repo: UserRepository, follow_repo: FollowRepository):
        super().__init__(repo)
        self.follow_repo = follow_repo

    async def get_user_profile(self, db: AsyncSession, *, user_id: int) -> UserProfile:
        """
        Получает и формирует профиль пользователя по ID.

        Включает загрузку и форматирование списков подписчиков и подписок.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (int): ID пользователя.

        Returns:
            UserProfile: Схема профиля пользователя.

        Raises:
            NotFoundError: Если пользователь не найден.
        """
        log.debug(f"Получение профиля для пользователя ID {user_id}")
        user = await self._get_obj_or_404(db, obj_id=user_id)

        # Получаем подписки и подписчиков с загруженными данными пользователей
        following_relations: Sequence[
            Follow
        ] = await self.follow_repo.get_following_with_users(db, follower_id=user_id)
        follower_relations: Sequence[
            Follow
        ] = await self.follow_repo.get_followers_with_users(db, following_id=user_id)

        # Преобразуем данные в формат схемы BaseUser
        following_list = [
            BaseUser.model_validate(f.followed_user) for f in following_relations
        ]
        followers_list = [
            BaseUser.model_validate(f.follower) for f in follower_relations
        ]

        profile = UserProfile(
            id=user.id,
            name=user.name,
            followers=followers_list,
            following=following_list,
        )
        log.info(f"Профиль для пользователя ID {user_id} успешно сформирован.")
        return profile
