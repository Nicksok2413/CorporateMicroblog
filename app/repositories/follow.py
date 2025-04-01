"""Репозиторий для работы с моделью Follow."""

from typing import List, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import log
from app.models.follow import Follow
from app.models.user import User  # Нужен для загрузки связей


# Аналогично Like, BaseRepository не очень подходит

class FollowRepository:
    """
    Репозиторий для управления подписками пользователей.
    """
    model = Follow

    async def get_follow(self, db: AsyncSession, *, follower_id: int, following_id: int) -> Optional[Follow]:
        """
        Проверяет наличие подписки одного пользователя на другого.

        Args:
            db: Асинхронная сессия SQLAlchemy
            follower_id: ID пользователя, который подписывается
            following_id: ID пользователя, на которого подписываются

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

    async def create_follow(self, db: AsyncSession, *, follower_id: int, following_id: int) -> Follow:
        """
        Создает запись о подписке.

        Args:
            db: Асинхронная сессия SQLAlchemy
            follower_id: ID пользователя-подписчика
            following_id: ID пользователя, на которого подписываются

        Returns:
            Follow: Созданный объект Follow.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных.
        """
        log.debug(f"Создание подписки: follower_id={follower_id}, following_id={following_id}")
        # Проверка на подписку на себя должна быть на уровне сервиса или API,
        # хотя и в БД есть CheckConstraint
        db_obj = self.model(follower_id=follower_id, following_id=following_id)
        db.add(db_obj)
        try:
            await db.commit()
            log.info(f"Подписка успешно создана: follower_id={follower_id}, following_id={following_id}")
            return db_obj
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при создании подписки (follower_id={follower_id}, following_id={following_id}): {exc}",
                      exc_info=True)
            raise exc

    async def remove_follow(self, db: AsyncSession, *, follower_id: int, following_id: int) -> bool:
        """
        Удаляет запись о подписке.

        Args:
            db: Асинхронная сессия SQLAlchemy
            follower_id: ID пользователя-подписчика
            following_id: ID пользователя, на которого подписаны

        Returns:
            bool: True, если подписка была найдена и удалена, иначе False.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных при удалении.
        """
        log.debug(f"Удаление подписки: follower_id={follower_id}, following_id={following_id}")
        statement = delete(self.model).where(
            self.model.follower_id == follower_id,
            self.model.following_id == following_id
        )
        try:
            result = await db.execute(statement)
            await db.commit()
            if result.rowcount > 0:
                log.info(f"Подписка успешно удалена: follower_id={follower_id}, following_id={following_id}")
                return True
            else:
                log.warning(f"Подписка для удаления не найдена: follower_id={follower_id}, following_id={following_id}")
                return False
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при удалении подписки (follower_id={follower_id}, following_id={following_id}): {exc}",
                      exc_info=True)
            raise exc

    async def get_following_ids(self, db: AsyncSession, *, follower_id: int) -> List[int]:
        """
        Получает список ID пользователей, на которых подписан данный пользователь.

        Args:
            db: Асинхронная сессия SQLAlchemy
            follower_id: ID пользователя-подписчика

        Returns:
            List[int]: Список ID пользователей, на которых он подписан.
        """
        log.debug(f"Получение ID подписок для пользователя {follower_id}")
        statement = select(self.model.following_id).where(self.model.follower_id == follower_id)
        result = await db.execute(statement)
        ids = result.scalars().all()
        log.debug(f"Пользователь {follower_id} подписан на {len(ids)} пользователей.")
        return ids

    async def get_follower_ids(self, db: AsyncSession, *, following_id: int) -> List[int]:
        """
        Получает список ID пользователей, которые подписаны на данного пользователя.

        Args:
            db: Асинхронная сессия SQLAlchemy
            following_id: ID пользователя, чьих подписчиков ищем

        Returns:
            List[int]: Список ID подписчиков.
        """
        log.debug(f"Получение ID подписчиков для пользователя {following_id}")
        statement = select(self.model.follower_id).where(self.model.following_id == following_id)
        result = await db.execute(statement)
        ids = result.scalars().all()
        log.debug(f"На пользователя {following_id} подписано {len(ids)} пользователей.")
        return ids

    async def get_following_with_users(self, db: AsyncSession, *, follower_id: int) -> Sequence[Follow]:
        """
        Получает список подписок пользователя с загрузкой информации о пользователях, на которых он подписан.

        Args:
            db: Асинхронная сессия SQLAlchemy
            follower_id: ID пользователя-подписчика

        Returns:
            Sequence[Follow]: Последовательность объектов Follow с загруженным `followed_user`.
        """
        stmt = (
            select(Follow)
            .where(Follow.follower_id == follower_id)
            .options(selectinload(Follow.followed_user))  # Загружаем профиль того, на кого подписан
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def get_followers_with_users(self, db: AsyncSession, *, following_id: int) -> Sequence[Follow]:
        """
        Получает список подписчиков пользователя с загрузкой информации об этих подписчиках.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            following_id: ID пользователя, чьих подписчиков ищем.

        Returns:
            Sequence[Follow]: Последовательность объектов Follow с загруженным `follower`.
        """
        stmt = (
            select(Follow)
            .where(Follow.following_id == following_id)
            .options(selectinload(Follow.follower))  # Загружаем профиль подписчика
        )
        res = await db.execute(stmt)
        return res.scalars().all()


# Создаем экземпляр репозитория
follow_repo = FollowRepository()
