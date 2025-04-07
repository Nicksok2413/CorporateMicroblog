"""Репозиторий для работы с моделью Follow."""

from typing import List, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import log
from src.models.follow import Follow


class FollowRepository:
    """
    Репозиторий для управления подписками пользователей.
    Не наследуется от BaseRepository из-за специфики модели Follow.
    """
    model = Follow

    async def get_follow(self, db: AsyncSession, *, follower_id: int, following_id: int) -> Optional[Follow]:
        """
        Проверяет наличие подписки одного пользователя на другого.

        Args:
            db (AsyncSession): Сессия БД.
            follower_id (int): ID пользователя, который подписывается.
            following_id (int): ID пользователя, на которого подписываются.

        Returns:
            Optional[Follow]: Объект Follow, если подписка существует, иначе None.
        """
        log.debug(f"Проверка подписки: follower_id={follower_id}, following_id={following_id}")

        statement = select(self.model).where(
            self.model.follower_id == follower_id,
            self.model.following_id == following_id
        )

        result = await db.execute(statement)
        return result.scalars().first()

    async def add_follow(self, db: AsyncSession, *, follower_id: int, following_id: int) -> Follow:
        """
        Создает и добавляет объект Follow в сессию.

        Args:
            db (AsyncSession): Сессия БД.
            follower_id (int): ID пользователя-подписчика.
            following_id (int): ID пользователя, на которого подписываются.

        Returns:
            Follow: Созданный объект Follow.
        """
        log.debug(f"Подготовка к добавлению подписки: follower_id={follower_id}, following_id={following_id}")
        db_obj = self.model(follower_id=follower_id, following_id=following_id)
        db.add(db_obj)
        return db_obj

    async def delete_follow(self, db: AsyncSession, *, follower_id: int, following_id: int) -> None:
        """
        Выполняет удаление записи о подписке напрямую в БД.

        Args:
            db (AsyncSession): Сессия БД.
            follower_id (int): ID пользователя-подписчика.
            following_id (int): ID пользователя, на которого подписаны.
        """
        log.debug(f"Подготовка к удалению подписки: follower_id={follower_id}, following_id={following_id}")

        statement = delete(self.model).where(
            self.model.follower_id == follower_id,
            self.model.following_id == following_id
        )

        await db.execute(statement)

    async def get_following_ids(self, db: AsyncSession, *, follower_id: int) -> List[int]:
        """
        Получает список ID пользователей, на которых подписан данный пользователь.

        Args:
            db (AsyncSession): Сессия БД.
            follower_id (int): ID пользователя-подписчика.

        Returns:
            List[int]: Список ID пользователей, на которых он подписан.
        """
        log.debug(f"Получение ID подписок для пользователя {follower_id}")
        statement = select(self.model.following_id).where(self.model.follower_id == follower_id)
        result = await db.execute(statement)
        ids = result.scalars().all()
        log.debug(f"Пользователь {follower_id} подписан на {len(ids)} пользователей.")
        return list(ids)

    async def get_following_with_users(self, db: AsyncSession, *, follower_id: int) -> Sequence[Follow]:
        """
        Получает список подписок пользователя с загрузкой информации о пользователях, на которых он подписан.

        Args:
            db (AsyncSession): Сессия БД.
            follower_id (int): ID пользователя-подписчика.

        Returns:
            Sequence[Follow]: Последовательность объектов Follow с загруженным `followed_user`.
        """
        log.debug(f"Получение подписок с деталями пользователей для follower_id={follower_id}")

        statement = (
            select(Follow)
            .where(Follow.follower_id == follower_id)
            .options(selectinload(Follow.followed_user))  # Загружаем профиль того, на кого подписан
        )

        result = await db.execute(statement)
        return result.scalars().all()

    async def get_followers_with_users(self, db: AsyncSession, *, following_id: int) -> Sequence[Follow]:
        """
        Получает список подписчиков пользователя с загрузкой информации об этих подписчиках.

        Args:
            db (AsyncSession): Сессия БД.
            following_id (int): ID пользователя, чьих подписчиков ищем.

        Returns:
            Sequence[Follow]: Последовательность объектов Follow с загруженным `follower`.
        """
        log.debug(f"Получение подписчиков с деталями пользователей для following_id={following_id}")

        statement = (
            select(Follow)
            .where(Follow.following_id == following_id)
            .options(selectinload(Follow.follower))  # Загружаем профиль подписчика
        )

        result = await db.execute(statement)
        return result.scalars().all()
