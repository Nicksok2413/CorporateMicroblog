"""Репозиторий для работы с моделью Like."""

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models.like import Like


# BaseRepository здесь не очень подходит, т.к. у Like составной PK и нет схем Create/Update
# Можно было бы унаследовать, но проще определить методы явно.

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
            db: Асинхронная сессия SQLAlchemy
            user_id: ID пользователя
            tweet_id: ID твита

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

    async def create_like(self, db: AsyncSession, *, user_id: int, tweet_id: int) -> Like:
        """
        Создает запись о лайке.

        Args:
            db: Асинхронная сессия SQLAlchemy
            user_id: ID пользователя
            tweet_id: ID твита

        Returns:
            Like: Созданный объект Like.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных.
        """
        log.debug(f"Создание лайка: user_id={user_id}, tweet_id={tweet_id}")
        db_obj = self.model(user_id=user_id, tweet_id=tweet_id)
        db.add(db_obj)
        try:
            await db.commit()
            # Refresh не обязателен для Like, т.к. нет автогенерируемых полей
            # await db.refresh(db_obj)
            log.info(f"Лайк успешно создан: user_id={user_id}, tweet_id={tweet_id}")
            return db_obj
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при создании лайка (user_id={user_id}, tweet_id={tweet_id}): {exc}", exc_info=True)
            raise exc

    async def remove_like(self, db: AsyncSession, *, user_id: int, tweet_id: int) -> bool:
        """
        Удаляет запись о лайке.

        Args:
            db: Асинхронная сессия SQLAlchemy
            user_id: ID пользователя
            tweet_id: ID твита

        Returns:
            bool: True, если лайк был найден и удален, иначе False.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных при удалении.
        """
        log.debug(f"Удаление лайка: user_id={user_id}, tweet_id={tweet_id}")
        statement = delete(self.model).where(
            self.model.user_id == user_id,
            self.model.tweet_id == tweet_id
        )
        try:
            result = await db.execute(statement)
            await db.commit()
            # result.rowcount > 0 означает, что строка была удалена
            if result.rowcount > 0:
                log.info(f"Лайк успешно удален: user_id={user_id}, tweet_id={tweet_id}")
                return True
            else:
                log.warning(f"Лайк для удаления не найден: user_id={user_id}, tweet_id={tweet_id}")
                return False
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при удалении лайка (user_id={user_id}, tweet_id={tweet_id}): {exc}", exc_info=True)
            raise exc


# Создаем экземпляр репозитория
like_repo = LikeRepository()
