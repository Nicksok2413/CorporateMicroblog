"""Сервис для работы с пользователями."""

from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import log
from app.models import Follow, User
from app.repositories import FollowRepository, UserRepository
from app.schemas.user import BaseUser, UserProfile
from app.services.base_service import BaseService


class UserService(BaseService[User, UserRepository]):
    """
    Сервис для бизнес-логики, связанной с пользователями.

    Включает получение профилей, управление подписками (через FollowService).
    """

    def __init__(self, repo: UserRepository, follow_repo: FollowRepository):
        super().__init__(repo)
        self.follow_repo = follow_repo

    async def get_user_by_id(self, db: AsyncSession, *, user_id: int) -> Optional[User]:
        """
        Получает пользователя по ID.

        Args:
            db: Сессия БД.
            user_id: ID пользователя.

        Returns:
            Найденный пользователь или None.
        """
        return await self.repo.get(db, obj_id=user_id)

    async def get_user_by_api_key(self, db: AsyncSession, *, api_key: str) -> Optional[User]:
        """
        Получает пользователя по API ключу.

        Args:
            db: Сессия БД.
            api_key: API ключ.

        Returns:
            Найденный пользователь или None.
        """
        return await self.repo.get_by_api_key(db, api_key=api_key)

    async def _get_user_or_404(self, db: AsyncSession, *, user_id: int) -> User:
        """
        Вспомогательный метод для получения пользователя по ID или выброса NotFoundError.

        Args:
            db: Сессия БД.
            user_id: ID пользователя.

        Returns:
            Найденный пользователь.

        Raises:
            NotFoundError: Если пользователь не найден.
        """
        user = await self.get_user_by_id(db, user_id=user_id)

        if not user:
            log.warning(f"Пользователь с ID {user_id} не найден.")
            raise NotFoundError(f"Пользователь с ID {user_id} не найден.")

        return user

    async def get_user_profile(self, db: AsyncSession, *, user_id: int) -> UserProfile:
        """
        Получает и формирует профиль пользователя по ID.

        Включает загрузку и форматирование списков подписчиков и подписок.

        Args:
            db: Сессия БД.
            user_id: ID пользователя.

        Returns:
            UserProfile: Схема профиля пользователя.

        Raises:
            NotFoundError: Если пользователь не найден.
        """
        log.debug(f"Получение профиля для пользователя ID {user_id}")
        user = await self._get_user_or_404(db, user_id=user_id)

        # Получаем подписки и подписчиков с загруженными данными пользователей
        following_relations: Sequence[Follow] = await self.follow_repo.get_following_with_users(db, follower_id=user_id)
        follower_relations: Sequence[Follow] = await self.follow_repo.get_followers_with_users(db, following_id=user_id)

        # Преобразуем данные в формат схемы BaseUser
        following_list = [BaseUser.model_validate(f.followed_user) for f in following_relations]
        followers_list = [BaseUser.model_validate(f.follower) for f in follower_relations]

        profile = UserProfile(
            id=user.id,
            name=user.name,
            followers=followers_list,
            following=following_list
        )
        log.info(f"Профиль для пользователя ID {user_id} успешно сформирован.")
        return profile
