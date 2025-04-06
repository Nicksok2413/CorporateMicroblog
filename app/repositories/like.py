"""Репозиторий для работы с моделью Like."""

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models.like import Like


class LikeRepository:
    """
    Репозиторий для управления лайками.
    Не наследуется от BaseRepository из-за специфики модели Like.
    """
    model = Like

    async def get_like(self, db: AsyncSession, *, user_id: int, tweet_id: int) -> Optional[Like]:
        """
        Проверяет наличие лайка от пользователя на конкретный твит.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (int): ID пользователя.
            tweet_id (int): ID твита.

        Returns:
            Optional[Like]: Объект Like, если лайк существует, иначе None.
        """
        log.debug(f"Проверка лайка: user_id={user_id}, tweet_id={tweet_id}")

        statement = select(self.model).where(
            self.model.user_id == user_id,
            self.model.tweet_id == tweet_id
        )

        result = await db.execute(statement)
        return result.scalars().first()

    async def add_like(self, db: AsyncSession, *, user_id: int, tweet_id: int) -> Like:
        """
        Создает и добавляет объект Like в сессию.

        Args:
            db (AsyncSession): Сессия БД.
            user_id (int): ID пользователя.
            tweet_id (int): ID твита.

        Returns:
            Like: Созданный объект Like.
        """
        log.debug(f"Подготовка к добавлению лайка: user_id={user_id}, tweet_id={tweet_id}")
        db_obj = self.model(user_id=user_id, tweet_id=tweet_id)
        db.add(db_obj)
        return db_obj

    async def delete_like(self, db: AsyncSession, *, user_id: int, tweet_id: int) -> None:
        """
        Выполняет удаление записи о лайке напрямую в БД (без загрузки объекта).

        Args:
            db (AsyncSession): Сессия БД.
            user_id (int): ID пользователя.
            tweet_id (int): ID твита.
        """
        log.debug(f"Подготовка к удалению лайка: user_id={user_id}, tweet_id={tweet_id}")

        statement = delete(self.model).where(
            self.model.user_id == user_id,
            self.model.tweet_id == tweet_id
        )

        await db.execute(statement)
