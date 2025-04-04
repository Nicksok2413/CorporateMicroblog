"""Сервис для работы с твитами."""

from typing import List, Optional, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (BadRequestError, ConflictError,
                                 PermissionDeniedError, NotFoundError)
from app.core.logging import log
from app.models import Media, Tweet, User
from app.repositories import FollowRepository, LikeRepository, MediaRepository, TweetRepository
from app.schemas.tweet import LikeInfo, TweetAuthor, TweetCreateRequest, TweetFeedResult, TweetInFeed
from app.services.base_service import BaseService
from app.services.media_service import MediaService


class TweetService(BaseService[Tweet, TweetRepository]):
    """
    Сервис для бизнес-логики, связанной с твитами.

    Включает создание, удаление, получение ленты, лайки/анлайки.
    """

    def __init__(
            self,
            repo: TweetRepository,
            media_repo: MediaRepository,
            like_repo: LikeRepository,
            follow_repo: FollowRepository,
            media_service: MediaService  # Зависимость от другого сервиса
    ):
        super().__init__(repo)
        self.media_repo = media_repo
        self.like_repo = like_repo
        self.follow_repo = follow_repo
        self.media_service = media_service  # Сохраняем медиа сервис

    async def _get_tweet_or_404(self, db: AsyncSession, tweet_id: int, load_details: bool = False) -> Tweet:
        """
        Вспомогательный метод для получения твита по ID или выброса NotFoundError.

        Args:
            db: Сессия БД.
            tweet_id: ID твита.
            load_details: Загружать ли связанные данные (автор, лайки, медиа).

        Returns:
            Найденный твит.

        Raises:
            NotFoundError: Если твит не найден.
        """
        log.debug(f"Поиск твита ID {tweet_id}{' с деталями' if load_details else ''}")

        if load_details:
            tweet = await self.repo.get_with_details(db, tweet_id=tweet_id)
        else:
            tweet = await self.repo.get(db, obj_id=tweet_id)

        if not tweet:
            log.warning(f"Твит с ID {tweet_id} не найден.")
            raise NotFoundError(f"Твит с ID {tweet_id} не найден.")
        return tweet

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
            db: Сессия БД.
            current_user: Пользователь, создающий твит.
            tweet_data: Данные для создания твита из API запроса.

        Returns:
            Созданный объект твита.

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
        except Exception as exc:
            await db.rollback()  # Откат при любой другой ошибке
            log.error(f"Ошибка при создании твита пользователем {current_user.id}: {exc}", exc_info=True)
            raise BadRequestError("Не удалось создать твит.") from exc

    async def delete_tweet(self, db: AsyncSession, current_user: User, *, tweet_id: int):
        """
        Удаляет твит, если он принадлежит текущему пользователю.

        Args:
            db: Сессия БД.
            current_user: Пользователь, выполняющий действие.
            tweet_id: ID твита для удаления.

        Raises:
            NotFoundError: Если твит не найден.
            ForbiddenException: Если пользователь пытается удалить чужой твит.
            BadRequestError: При ошибке удаления из БД.
        """
        log.info(f"Пользователь ID {current_user.id} пытается удалить твит ID {tweet_id}")
        tweet = await self._get_tweet_or_404(db, tweet_id)

        if tweet.author_id != current_user.id:
            log.warning(
                f"Пользователь ID {current_user.id} не имеет прав на удаление твита ID {tweet_id}. "
                f"(ID автора твита {tweet.author_id})."
            )
            raise PermissionDeniedError("Вы не можете удалить этот твит.")

        try:
            deleted_obj = await self.repo.remove(db, obj_id=tweet_id)
            if not deleted_obj:
                raise NotFoundError(f"Твит с ID {tweet_id} не найден для удаления (внутренняя ошибка).")
            await db.commit()
            log.success(f"Твит ID {tweet_id} успешно удален пользователем ID {current_user.id}.")
        except (NotFoundError, PermissionDeniedError):  # Перевыбрасываем ошибки прав и ненайденного объекта
            raise
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при удалении твита ID {tweet_id} пользователем {current_user.id}: {exc}", exc_info=True)
            raise BadRequestError("Не удалось удалить твит.") from exc

    async def like_tweet(self, db: AsyncSession, current_user: User, *, tweet_id: int):
        """
        Ставит лайк на твит от имени текущего пользователя.

        Args:
            db: Сессия БД.
            current_user: Пользователь, ставящий лайк.
            tweet_id: ID твита.

        Raises:
            NotFoundError: Если твит не найден.
            ConflictException: Если пользователь уже лайкнул этот твит.
            BadRequestError: При ошибке сохранения лайка.
        """
        log.info(f"Пользователь ID {current_user.id} лайкает твит ID {tweet_id}")
        await self._get_tweet_or_404(db, tweet_id)  # Проверяем, существует ли твит

        # Проверяем, не лайкнул ли уже
        existing_like = await self.like_repo.get_like(db, user_id=current_user.id, tweet_id=tweet_id)

        if existing_like:
            log.warning(f"Пользователь ID {current_user.id} уже лайкнул твит ID {tweet_id}.")
            raise ConflictError("Вы уже лайкнули этот твит.")

        try:
            await self.like_repo.add_like(db, user_id=current_user.id, tweet_id=tweet_id)
            await db.commit()
            log.success(f"Лайк от пользователя ID {current_user.id} на твит ID {tweet_id} успешно поставлен.")
        except IntegrityError as exc:
            # На случай гонки запросов или если проверка выше не сработала
            await db.rollback()
            log.warning(f"Конфликт целостности при лайке твита ID {tweet_id} пользователем ID {current_user.id}: {exc}")
            raise ConflictError("Не удалось поставить лайк (возможно, уже существует).") from exc
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при создании лайка для твита ID {tweet_id} пользователем ID {current_user.id}: {exc}",
                      exc_info=True)
            raise BadRequestError("Не удалось поставить лайк.") from exc

    async def unlike_tweet(self, db: AsyncSession, current_user: User, *, tweet_id: int):
        """
        Убирает лайк с твита от имени текущего пользователя.

        Args:
            db: Сессия БД.
            current_user: Пользователь, убирающий лайк.
            tweet_id: ID твита.

        Raises:
            NotFoundError: Если лайк для удаления не найден (твит не лайкнут этим пользователем).
            BadRequestError: При ошибке удаления лайка.
        """
        log.info(f"Пользователь ID {current_user.id} убирает лайк с твита ID {tweet_id}")

        existing_like = await self.like_repo.get_like(db, user_id=current_user.id, tweet_id=tweet_id)

        if not existing_like:
            log.warning(f"Лайк от пользователя ID {current_user.id} на твит ID {tweet_id} не найден для удаления.")
            raise NotFoundError("Лайк не найден или уже удален.")

        try:
            await self.like_repo.remove_like(db, user_id=current_user.id, tweet_id=tweet_id)
            await db.commit()
            log.success(f"Лайк от пользователя ID {current_user.id} на твит ID {tweet_id} успешно удален.")
        except Exception as exc:
            await db.rollback()
            log.error(f"Ошибка при удалении лайка для твита ID {tweet_id} пользователем ID {current_user.id}: {exc}",
                      exc_info=True)
            raise BadRequestError("Не удалось убрать лайк.") from exc

    async def get_tweet_feed(self, db: AsyncSession, *, current_user: User) -> TweetFeedResult:
        """
        Формирует ленту твитов для текущего пользователя.

        Включает твиты от пользователей, на которых он подписан, и его собственные.
        Сортирует по популярности (лайки) и дате.

        Args:
            db: Сессия БД.
            current_user: Пользователь, для которого формируется лента.

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
