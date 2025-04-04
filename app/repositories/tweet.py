"""Репозиторий для работы с моделью Tweet."""

from typing import List, Optional, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import log
from app.models import Like, Media, Tweet
from app.repositories.base import BaseRepository
from app.schemas.tweet import TweetCreateInternal


class TweetRepository(BaseRepository[Tweet, TweetCreateInternal, None]):
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
            db: Асинхронная сессия SQLAlchemy.
            content: Содержимое твита.
            author_id: ID автора твита.
            media_items: Список объектов Media для прикрепления (опционально).

        Returns:
            Tweet: Созданный объект твита.
        """
        log.debug(f"Подготовка к созданию твита для автора ID {author_id} с медиа: {'Да' if media_items else 'Нет'}")
        db_obj = Tweet(content=content, author_id=author_id)

        if media_items:
            # Присоединяем медиа к твиту (SQLAlchemy обработает M2M связь)
            db_obj.attachments.extend(media_items)

        db.add(db_obj)
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
        и сортирует по популярности (количество лайков убыв.), затем по дате создания (убыв.).

        Args:
            db: Асинхронная сессия SQLAlchemy.
            author_ids: Список ID авторов, чьи твиты нужно включить.

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
            # Сортировка: сначала по количеству лайков (NULLS LAST), затем по дате создания
            .order_by(
                desc(func.coalesce(like_count_subquery.c.like_count, 0))  # Сортировка по лайкам, NULL -> 0
            )
        )

        result = await db.execute(statement)
        # Используем unique() для корректной обработки LEFT JOIN при загрузке связей
        tweets = result.unique().scalars().all()
        log.debug(f"Найдено {len(tweets)} твитов для ленты.")
        return tweets

    async def get_with_details(self, db: AsyncSession, tweet_id: int) -> Optional[Tweet]:
        """
        Получает твит по ID с загруженными связанными данными (автор, лайки, медиа).

        Args:
            db: Асинхронная сессия SQLAlchemy.
            tweet_id: ID твита.

        Returns:
            Optional[Tweet]: Найденный твит с загруженными деталями или None.
        """
        log.debug(f"Получение твита с деталями по ID: {tweet_id}")
        statement = (
            select(self.model)
            .where(self.model.id == tweet_id)
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.likes).selectinload(Like.user),
                selectinload(Tweet.attachments)
            )
        )
        result = await db.execute(statement)
        instance = result.unique().scalars().first()
        if instance:
            log.debug(f"Твит с деталями (ID {tweet_id}) найден.")
        else:
            log.debug(f"Твит с деталями (ID {tweet_id}) не найден.")
        return instance
