"""Репозиторий для работы с моделью Tweet."""

from typing import List, Optional, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import log
from app.models import Like, Media, Tweet
from app.repositories.base import BaseRepository
from app.schemas.tweet import TweetCreateInternal


class TweetRepository(BaseRepository[Tweet, TweetCreateInternal]):
    """Репозиторий для выполнения CRUD операций с моделью Tweet."""

    async def create_with_author_and_media(
            self,
            db: AsyncSession,
            *,
            content: str,
            author_id: int,
            media_items: Optional[List[Media]] = None
    ) -> Tweet:
        """
        Создает и добавляет твит в сессию, связывая его с автором и медиафайлами.

        Это специфичный метод, более удобный, чем базовый create,
        когда нужно сразу прикрепить медиа.

        Args:
            db (AsyncSession): Сессия БД.
            content (str): Содержимое твита.
            author_id (int): ID автора твита.
            media_items (Optional[List[Media]]): Список объектов Media для прикрепления (опционально).

        Returns:
            Tweet: Созданный объект твита.
        """
        log.debug(f"Подготовка к созданию твита для автора ID {author_id} с медиа: {'Да' if media_items else 'Нет'}")
        db_obj = Tweet(content=content, author_id=author_id)

        if media_items:
            # Присоединяем медиа к твиту (SQLAlchemy обработает M2M связь)
            db_obj.attachments.extend(media_items)

        await self.add(db, db_obj=db_obj)
        return db_obj

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
