"""Сервис для работы с твитами."""

from typing import List, Optional, Sequence

from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from src.core.logging import log
from src.models import Media, Tweet, User
from src.repositories import FollowRepository, MediaRepository, TweetRepository
from src.schemas.tweet import LikeInfo, TweetAuthor, TweetCreateRequest, TweetFeedResult, TweetInFeed
from src.services.base_service import BaseService
from src.services.media_service import MediaService


class TweetService(BaseService[Tweet, TweetRepository]):
    """
    Сервис для бизнес-логики, связанной с твитами.

    Включает создание, удаление, получение ленты, лайки/анлайки.
    """

    def __init__(
            self,
            repo: TweetRepository,
            follow_repo: FollowRepository,
            media_repo: MediaRepository,
            media_service: MediaService  # Зависимость от медиа сервиса
    ):
        super().__init__(repo)
        self.follow_repo = follow_repo
        self.media_repo = media_repo
        self.media_service = media_service

    async def create_tweet(
            self,
            db: AsyncSession,
            current_user: User,
            *,
            tweet_data: TweetCreateRequest
    ) -> Tweet:
        """
        Создает новый твит для указанного пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            current_user (User): Пользователь, создающий твит.
            tweet_data (TweetCreateRequest): Данные для создания твита из API запроса.

        Returns:
            Tweet: Созданный объект твита.

        Raises:
            NotFoundError: Если указанный media_id не найден.
            BadRequestError: При ошибке сохранения в БД.
        """
        log.info(f"Пользователь ID {current_user.id} создает твит.")
        media_attachments: List[Media] = []
        tweet: Optional[Tweet] = None

        try:
            if tweet_data.tweet_media_ids:
                log.debug(f"Прикрепление медиа ID: {tweet_data.tweet_media_ids}")
                for media_id in tweet_data.tweet_media_ids:
                    media = await self.media_repo.get(db, obj_id=media_id)
                    if not media:
                        log.warning(f"Медиа с ID {media_id} не найдено при создании твита.")
                        raise NotFoundError(f"Медиафайл с ID {media_id} не найден.")
                    media_attachments.append(media)

            tweet = await self.repo.create_with_author_and_media(
                db=db,
                content=tweet_data.tweet_data,
                author_id=current_user.id,
                media_items=media_attachments
            )
            await db.commit()
            await db.refresh(tweet, attribute_names=['attachments'])
            log.success(f"Твит ID {tweet.id} успешно создан пользователем {current_user.id}")
            return tweet
        except NotFoundError:
            raise
        except SQLAlchemyError as exc:
            await db.rollback()
            log.error(f"Ошибка при создании твита пользователем {current_user.id}: {exc}", exc_info=True)
            raise BadRequestError("Не удалось создать твит.") from exc

    async def delete_tweet(self, db: AsyncSession, current_user: User, *, tweet_id: int) -> None:
        """
        Удаляет твит и связанные с ним медиафайлы.

        Args:
            db (AsyncSession): Сессия БД.
            current_user (User): Пользователь, выполняющий действие.
            tweet_id (id): ID твита для удаления.

        Raises:
            NotFoundError: Если твит не найден.
            PermissionDeniedError: Если пользователь пытается удалить чужой твит.
            BadRequestError: При ошибке удаления из БД или файла.
        """
        log.info(f"Пользователь ID {current_user.id} пытается удалить твит ID {tweet_id}")

        # Получаем твит
        tweet_to_delete = await self.repo.get_with_attachments(db, tweet_id=tweet_id)

        if not tweet_to_delete:
            raise NotFoundError(f"Твит с ID {tweet_id} не найден.")

        # Проверяем права доступа
        if tweet_to_delete.author_id != current_user.id:
            log.warning(
                f"Пользователь ID {current_user.id} не имеет прав на удаление твита ID {tweet_id}. "
                f"(ID автора твита {tweet_to_delete.author_id})."
            )
            raise PermissionDeniedError("Вы не можете удалить этот твит.")

        # Сохраняем список медиа ОБЪЕКТОВ этого твита
        media_to_delete: List[Media] = list(tweet_to_delete.attachments)
        # Собираем пути файлов для физического удаления
        media_files_to_delete_paths: List[str] = [m.file_path for m in media_to_delete]

        try:
            # Помечаем сам твит для удаления (CASCADE удалит строки в tweet_media_association)
            await self.repo.delete(db, db_obj=tweet_to_delete)
            log.debug(f"Твит ID {tweet_id} помечен для удаления.")

            # Помечаем связанные объекты Media для удаления
            if media_to_delete:
                log.info(f"Пометка на удаление {len(media_to_delete)} связанных медиа записей...")
                for media in media_to_delete:
                    await self.media_repo.delete(db, db_obj=media)

            # Коммитим изменения в БД (удаление твита, связей, и записей Media)
            await db.commit()
            log.success(f"Твит ID {tweet_id} и {len(media_to_delete)} связанных медиа записей успешно удалены из БД.")

            # Удаляем физические файлы ПОСЛЕ успешного коммита
            if media_files_to_delete_paths:
                log.info(f"Удаление {len(media_files_to_delete_paths)} физических медиафайлов...")
                await self.media_service.delete_media_files(media_files_to_delete_paths)

        except (NotFoundError, PermissionDeniedError):
            # Эти ошибки уже обработаны, просто пробрасываем дальше
            await db.rollback()  # Откатываем, если ошибка произошла до commit
            raise
        except SQLAlchemyError as exc:
            await db.rollback()
            log.error(f"Ошибка БД при удалении твита ID {tweet_id} или медиа: {exc}", exc_info=True)
            # Не пытаемся удалять файлы, если БД не удалось обновить
            raise BadRequestError("Не удалось удалить твит или связанные медиа из базы данных.") from exc
        except Exception as exc:
            # Ловим другие возможные ошибки (например, при удалении файлов)
            await db.rollback()  # Откатываем БД, если что-то пошло не так после commit
            log.error(f"Ошибка при физическом удалении файлов для твита ID {tweet_id}: {exc}", exc_info=True)
            # ВАЖНО: Данные из БД уже могли удалиться! Ситуация неидеальна.
            # Можно добавить логику повторной попытки удаления файлов позже.
            # Пока просто сообщаем об общей ошибке.
            raise BadRequestError("Произошла ошибка при удалении твита и/или его медиафайлов.") from exc

    async def get_tweet_feed(self, db: AsyncSession, current_user: User) -> TweetFeedResult:
        """
        Формирует ленту твитов для текущего пользователя.

        Включает твиты от пользователей, на которых он подписан, и его собственные.
        Сортирует по популярности (лайки) и дате.

        Args:
            db (AsyncSession): Сессия БД.
            current_user (User): Пользователь, для которого формируется лента.

        Returns:
            TweetFeedResult: Схема с лентой твитов.
        """
        log.info(f"Формирование ленты для пользователя ID {current_user.id}")
        following_ids = await self.follow_repo.get_following_ids(db, follower_id=current_user.id)

        # Включаем ID самого пользователя в список авторов
        author_ids_to_fetch = list(set(following_ids + [current_user.id]))
        log.debug(f"ID авторов для ленты пользователя {current_user.id}: {author_ids_to_fetch}")

        # Получаем твиты из репозитория (уже с загруженными связями и сортировкой)
        tweets_db: Sequence[Tweet] = await self.repo.get_feed_for_user(
            db, author_ids=author_ids_to_fetch
        )

        # Форматируем твиты в схему TweetInFeed
        feed_tweets: List[TweetInFeed] = []

        for tweet in tweets_db:
            # Формируем URL для медиа
            attachment_urls = [self.media_service.get_media_url(media) for media in tweet.attachments]
            # Формируем информацию об авторе
            author_info = TweetAuthor.model_validate(tweet.author)
            # Формируем информацию о лайках
            likes_info = [LikeInfo.model_validate(like.user) for like in tweet.likes]

            feed_tweets.append(
                TweetInFeed(
                    id=tweet.id,
                    content=tweet.content,
                    attachments=attachment_urls,
                    author=author_info,
                    likes=likes_info,
                )
            )

        log.info(f"Лента для пользователя ID {current_user.id} сформирована, {len(feed_tweets)} твитов.")
        return TweetFeedResult(tweets=feed_tweets)
