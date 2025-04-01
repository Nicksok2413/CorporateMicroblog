"""Репозиторий для работы с медиафайлами в БД."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media


class MediaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_media(
            self,
            user_id: int,
            filename: str
    ) -> Media:
        """Создает запись о медиафайле в БД.

        Args:
            user_id: ID пользователя
            filename: Имя файла

        Returns:
            Media: Созданный объект
        """
        media = Media(
            user_id=user_id,
            filename=filename
        )
        self.session.add(media)
        await self.session.commit()
        return media


# v2
# """Репозиторий для работы с медиафайлами в БД."""
#
# from typing import List, Optional
# from sqlalchemy import select, func, and_
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.models.media import Media, TweetMedia
# from app.models.user import User
# from app.core.exceptions import NotFoundError
#
#
# class MediaRepository:
#     def __init__(self, session: AsyncSession):
#         """
#         Инициализация репозитория.
#
#         Args:
#             session: Асинхронная сессия SQLAlchemy
#         """
#         self.session = session
#
#     async def get_by_id(self, media_id: int) -> Optional[Media]:
#         """
#         Получение медиафайла по ID.
#
#         Args:
#             media_id: ID медиафайла
#
#         Returns:
#             Optional[Media]: Найденный объект или None
#         """
#         result = await self.session.execute(
#             select(Media).where(Media.id == media_id)
#         return result.scalar_one_or_none()
#
#     async def get_user_media(self, user_id: int, limit: int = 100) -> List[Media]:
#         """
#         Получение медиафайлов пользователя.
#
#         Args:
#             user_id: ID пользователя
#             limit: Максимальное количество
#
#         Returns:
#             List[Media]: Список медиафайлов
#         """
#         result = await self.session.execute(
#             select(Media)
#             .where(Media.user_id == user_id)
#             .order_by(Media.id.desc())
#             .limit(limit)
#         )
#         return result.scalars().all()
#
#     async def create_media(
#             self,
#             user_id: int,
#             filename: str,
#             content_type: str
#     ) -> Media:
#         """
#         Создание записи о медиафайле.
#
#         Args:
#             user_id: ID пользователя
#             filename: Имя файла
#             content_type: MIME-тип
#
#         Returns:
#             Media: Созданный объект
#
#         Raises:
#             ValueError: Если файл с таким именем уже существует
#         """
#         # Проверка уникальности имени файла
#         existing = await self.session.execute(
#             select(Media).where(Media.filename == filename))
#         if existing.scalar_one_or_none():
#             raise ValueError("Файл с таким именем уже существует")
#
#         media = Media(
#             user_id=user_id,
#             filename=filename,
#             content_type=content_type
#         )
#         self.session.add(media)
#         await self.session.commit()
#         await self.session.refresh(media)
#         return media
#
#     async def delete_media(self, media_id: int) -> bool:
#         """
#         Удаление медиафайла.
#
#         Args:
#             media_id: ID медиафайла
#
#         Returns:
#             bool: True если удаление прошло успешно
#
#         Raises:
#             NotFoundError: Если медиафайл не найден
#         """
#         media = await self.get_by_id(media_id)
#         if not media:
#             raise NotFoundError("Медиафайл не найден")
#
#         await self.session.delete(media)
#         await self.session.commit()
#         return True
#
#     async def attach_to_tweet(
#             self,
#             tweet_id: int,
#             media_id: int,
#             position: int = 0
#     ) -> TweetMedia:
#         """
#         Прикрепление медиафайла к твиту.
#
#         Args:
#             tweet_id: ID твита
#             media_id: ID медиафайла
#             position: Позиция в списке
#
#         Returns:
#             TweetMedia: Созданная связь
#
#         Raises:
#             NotFoundError: Если медиафайл не найден
#         """
#         media = await self.get_by_id(media_id)
#         if not media:
#             raise NotFoundError("Медиафайл не найден")
#
#         link = TweetMedia(
#             tweet_id=tweet_id,
#             media_id=media_id,
#             position=position
#         )
#         self.session.add(link)
#         await self.session.commit()
#         return link
#
#     async def get_tweet_media(self, tweet_id: int) -> List[Media]:
#         """
#         Получение медиафайлов твита.
#
#         Args:
#             tweet_id: ID твита
#
#         Returns:
#             List[Media]: Список медиафайлов
#         """
#         result = await self.session.execute(
#             select(Media)
#             .join(TweetMedia, Media.id == TweetMedia.media_id)
#             .where(TweetMedia.tweet_id == tweet_id)
#             .order_by(TweetMedia.position)
#         )
#         return result.scalars().all()
#
#     async def count_user_media(self, user_id: int) -> int:
#         """
#         Подсчет количества медиафайлов пользователя.
#
#         Args:
#             user_id: ID пользователя
#
#         Returns:
#             int: Количество медиафайлов
#         """
#         result = await self.session.execute(
#             select(func.count())
#             .where(Media.user_id == user_id)
#         )
#         return result.scalar_one()
#
#     async def validate_media_ownership(
#             self,
#             media_ids: List[int],
#             user_id: int
#     ) -> bool:
#         """
#         Проверка принадлежности медиафайлов пользователю.
#
#         Args:
#             media_ids: Список ID медиафайлов
#             user_id: ID пользователя
#
#         Returns:
#             bool: True если все файлы принадлежат пользователю
#
#         Raises:
#             NotFoundError: Если какой-то файл не найден
#         """
#         if not media_ids:
#             return True
#
#         result = await self.session.execute(
#             select(func.count(Media.id))
#             .where(and_(
#                 Media.id.in_(media_ids),
#                 Media.user_id != user_id
#             ))
#         )
#         invalid_count = result.scalar_one()
#
#         if invalid_count > 0:
#             raise NotFoundError("Некоторые медиафайлы не найдены или не принадлежат пользователю")
#
#         return True