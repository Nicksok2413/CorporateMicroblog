"""Репозиторий для работы с моделью Tweet."""

from typing import List, Optional, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import log
from src.models import Like, Tweet
from src.repositories.base import BaseRepository
from src.schemas.tweet import TweetCreateInternal


class TweetRepository(BaseRepository[Tweet, TweetCreateInternal]):
    """Репозиторий для выполнения CRUD операций с моделью Tweet."""

    async def get_with_attachments(self, db: AsyncSession, *, tweet_id: int) -> Optional[Tweet]:
        """
        Получает твит по ID с загрузкой связанных медиафайлов.

        Args:
            db (AsyncSession): Сессия БД.
            tweet_id (int): ID твита.

        Returns:
            Optional[Tweet]: Найденный твит с загруженными attachments или None.
        """
        log.debug(f"Получение твита ID {tweet_id} с загрузкой медиа")

        statement = (
            select(self.model)
            .where(self.model.id == tweet_id)
            .options(
                selectinload(self.model.attachments)
            )
        )

        result = await db.execute(statement)
        instance = result.scalars().first()

        if instance:
            log.debug(f"Твит ID {tweet_id} с медиа найден.")
        else:
            log.debug(f"Твит ID {tweet_id} не найден.")

        return instance

    async def get_feed_for_user(
            self,
            db: AsyncSession,
            *,
            author_ids: List[int],
    ) -> Sequence[Tweet]:
        """
        Получает ленту твитов для пользователя от указанных авторов.

        Загружает связанные данные (автор, лайки + их пользователи, медиа)
        и сортирует по популярности (количество лайков убыв.).

        Args:
            db (AsyncSession): Сессия БД.
            author_ids (List[int]): Список ID авторов, чьи твиты нужно включить.

        Returns:
            Sequence[Tweet]: Последовательность объектов Tweet с загруженными связями.
        """
        if not author_ids:
            log.debug("Список ID авторов для ленты пуст.")
            return []

        log.debug(f"Получение ленты твитов для авторов {author_ids}")

        # Подзапрос для подсчета лайков
        like_count_subquery = (
            select(Like.tweet_id, func.count(Like.user_id).label("like_count"))
            .group_by(Like.tweet_id)
            .subquery()
        )

        statement = (
            select(Tweet)
            .where(Tweet.author_id.in_(author_ids))
            # Присоединяем подзапрос с количеством лайков
            .outerjoin(like_count_subquery, Tweet.id == like_count_subquery.c.tweet_id)
            # Используем selectinload для эффективной загрузки связей
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.likes).selectinload(Like.user),  # Загружаем лайки и пользователей
                selectinload(Tweet.attachments)  # Загружаем медиа
            )
            # Сортировка: по убыванию лайков, NULL значения (0 лайков) в конце
            .order_by(
                desc(like_count_subquery.c.like_count).nulls_last()
            )
        )

        result = await db.execute(statement)
        # Используем unique() для корректной обработки JOIN при загрузке связей
        tweets = result.unique().scalars().all()
        log.debug(f"Найдено {len(tweets)} твитов для ленты.")
        return tweets
