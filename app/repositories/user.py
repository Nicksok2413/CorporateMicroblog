"""Репозиторий для работы с пользователями в БД."""

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.tweet import Tweet
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Логика работы с пользователями в БД."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_api_key(self, api_key: str) -> User | None:
        """Находит пользователя по API-ключу.

        Args:
            api_key: Ключ аутентификации

        Returns:
            User | None: Объект пользователя или None
        """
        result = await self.session.execute(select(User).filter_by(api_key=api_key))
        return result.scalar_one_or_none()

    async def create_user(
            self,
            name: str,
            api_key: str,
            is_demo: bool = False
    ) -> User:
        """Создает нового пользователя.

        Args:
            name: Имя пользователя
            api_key: Ключ аутентификации
            is_demo: Флаг демо-аккаунта

        Returns:
            User: Созданный пользователь

        Raises:
            ValueError: Если пользователь с таким api_key уже существует
        """
        existing_user = await self.get_by_api_key(api_key)
        if existing_user:
            raise ValueError("Пользователь с таким API-ключом уже существует")

        user = User(
            name=name,
            api_key=api_key,
            is_demo=is_demo
        )
        self.session.add(user)
        await self.session.commit()
        return user

    async def get_users_with_stats(
            self,
            limit: int = 100,
            offset: int = 0
    ) -> list[tuple[User, int, int]]:
        """Возвращает список пользователей со статистикой.

        Args:
            limit: Максимальное количество записей
            offset: Смещение

        Returns:
            list: Список кортежей (пользователь, кол-во твитов, кол-во подписчиков)
        """
        query = (
            select(
                User,
                func.count(distinct(Tweet.id)),
                func.count(distinct(Follow.follower_id))
            )
            .outerjoin(Tweet, User.id == Tweet.author_id)
            .outerjoin(Follow, User.id == Follow.followed_id)
            .group_by(User.id)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return result.all()


    # v2
    # async def get_with_stats(self, user_id: int) -> tuple[User, int, int]:
    #     """Возвращает пользователя с кол-вом твитов и подписчиков."""
    #     result = await self.session.execute(
    #         select(
    #             User,
    #             func.count(distinct(Follow.follower_id)),
    #             func.count(distinct(Tweet.id))
    #         )
    #         .outerjoin(Follow, User.id == Follow.followed_id)
    #         .outerjoin(Tweet, User.id == Tweet.author_id)
    #         .where(User.id == user_id)
    #         .group_by(User.id)
    #     )
    #     return result.first()
