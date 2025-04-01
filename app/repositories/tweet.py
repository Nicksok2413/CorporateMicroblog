"""Репозиторий для работы с моделью Tweet."""

from typing import List, Optional, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import log
from app.models import Like, Media, Tweet, User  # Импортируем все нужные модели
from app.repositories.base import BaseRepository
# Импортируем внутреннюю схему для базового метода create
# (предполагается, что она создана в schemas/tweet.py)
from app.schemas.tweet import TweetCreateInternal  # Убедитесь, что эта схема существует!


# Если схемы TweetUpdate нет, используем None


class TweetRepository(BaseRepository[Tweet, TweetCreateInternal, None]):  # Указываем схемы
    """
    Репозиторий для выполнения CRUD операций с моделью Tweet.
    """

    # Базовый метод create унаследован и ожидает TweetCreateInternal

    async def create_with_author_and_media(
            self,
            db: AsyncSession,
            *,
            content: str,
            author_id: int,
            media_items: Optional[List[Media]] = None
    ) -> Tweet:
        """
        Создает твит, связывая его с автором и медиафайлами.

        Это специфичный метод, более удобный, чем базовый create,
        когда нужно сразу прикрепить медиа.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            content: Содержимое твита.
            author_id: ID автора твита.
            media_items: Список объектов Media для прикрепления (опционально).

        Returns:
            Tweet: Созданный объект твита.

        Raises:
            SQLAlchemyError: В случае ошибки базы данных.
        """
        log.debug(f"Создание твита для автора ID {author_id} с медиа: {'Да' if media_items else 'Нет'}")
        # Создаем объект Tweet напрямую
        db_obj = Tweet(content=content, author_id=author_id)
        if media_items:
            # Присоединяем медиа к твиту (SQLAlchemy обработает M2M связь)
            db_obj.attachments.extend(media_items)

        db.add(db_obj)
        try:
            await db.commit()
            # Обновляем объект, чтобы получить связанные данные, если нужно
            # Особенно важно для many-to-many, чтобы увидеть attachments
            await db.refresh(db_obj, attribute_names=['attachments'])
            log.info(f"Успешно создан твит ID {db_obj.id} для автора {author_id}.")
            return db_obj
        except Exception as e:  # Ловим общую ошибку для отката
            await db.rollback()
            log.error(f"Ошибка при создании твита для автора {author_id}: {e}", exc_info=True)
            raise e  # Передаем исключение выше

    async def get_feed_for_user(
            self,
            db: AsyncSession,
            *,
            author_ids: List[int],
            limit: int = 50,
            offset: int = 0,
    ) -> Sequence[Tweet]:
        """
        Получает ленту твитов для пользователя от указанных авторов.

        Загружает связанные данные (автор, лайки + их пользователи, медиа)
        и сортирует по популярности (количество лайков убыв.), затем по дате создания (убыв.).

        Args:
            db: Асинхронная сессия SQLAlchemy.
            author_ids: Список ID авторов, чьи твиты нужно включить.
            limit: Максимальное количество твитов.
            offset: Смещение для пагинации.

        Returns:
            Sequence[Tweet]: Последовательность объектов Tweet с загруженными связями.
        """
        if not author_ids:
            log.debug("Список ID авторов для ленты пуст.")
            return []

        log.debug(f"Получение ленты твитов для авторов {author_ids} (limit={limit}, offset={offset})")

        # Подзапрос для подсчета лайков
        like_count_subquery = (
            select(Like.tweet_id, func.count(Like.user_id).label("like_count"))
            .group_by(Like.tweet_id)
            .subquery()
        )

        statement = (
            select(Tweet)
            .where(Tweet.author_id.in_(author_ids))
            # Присоединяем подзапрос с количеством лайков (LEFT JOIN)
            .outerjoin(like_count_subquery, Tweet.id == like_count_subquery.c.tweet_id)
            # Используем selectinload для эффективной загрузки связей
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.likes).selectinload(Like.user),  # Загружаем лайки и пользователей
                selectinload(Tweet.attachments)  # Загружаем медиа
            )
            # Сортировка: сначала по количеству лайков (NULLS LAST), затем по дате создания
            .order_by(
                desc(func.coalesce(like_count_subquery.c.like_count, 0)),  # Сортировка по лайкам, NULL -> 0
                desc(Tweet.created_at)  # Вторичная сортировка по дате
            )
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(statement)
        # Используем unique() для корректной обработки LEFT JOIN при загрузке связей
        tweets = result.unique().scalars().all()
        log.debug(f"Найдено {len(tweets)} твитов для ленты.")
        return tweets

    async def get_with_details(self, db: AsyncSession, id: int) -> Optional[Tweet]:
        """
        Получает твит по ID с загруженными связанными данными (автор, лайки, медиа).

        Args:
            db: Асинхронная сессия SQLAlchemy.
            id: ID твита.

        Returns:
            Optional[Tweet]: Найденный твит с загруженными деталями или None.
        """
        log.debug(f"Получение твита с деталями по ID: {id}")
        statement = (
            select(self.model)
            .where(self.model.id == id)
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.likes).selectinload(Like.user),
                selectinload(Tweet.attachments)
            )
        )
        result = await db.execute(statement)
        instance = result.unique().scalars().first()
        if instance:
            log.debug(f"Твит с деталями (ID {id}) найден.")
        else:
            log.debug(f"Твит с деталями (ID {id}) не найден.")
        return instance


# Создаем экземпляр репозитория
tweet_repo = TweetRepository(Tweet)
