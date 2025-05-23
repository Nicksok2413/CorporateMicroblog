"""Сервис для управления лайками."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestError, NotFoundError
from src.core.logging import log
from src.models.user import User
from src.repositories import LikeRepository, TweetRepository


class LikeService:
    """
    Сервис для бизнес-логики, связанной с лайками.

    Не наследуется от BaseService, так как работает с репозиторием Like,
    но основная логика связана с проверкой Tweet.
    """

    def __init__(self, repo: LikeRepository, tweet_repo: TweetRepository):
        self.repo = repo
        self.tweet_repo = tweet_repo

    async def like_tweet(
        self, db: AsyncSession, current_user: User, *, tweet_id: int
    ) -> None:
        """
        Ставит лайк на твит от имени текущего пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            current_user (User): Пользователь, ставящий лайк.
            tweet_id (int): ID твита.

        Raises:
            NotFoundError: Если твит не найден.
            ConflictError: Если пользователь уже лайкнул этот твит.
            BadRequestError: При ошибке сохранения лайка.
        """
        log.info(f"Пользователь ID {current_user.id} лайкает твит ID {tweet_id}")

        # Проверяем, существует ли твит
        tweet = await self.tweet_repo.get(db, obj_id=tweet_id)

        if not tweet:
            log.warning(f"Твит с ID {tweet_id} не найден при попытке лайка.")
            raise NotFoundError(f"Твит с ID {tweet_id} не найден.")

        try:
            await self.repo.add_like(db, user_id=current_user.id, tweet_id=tweet_id)
            await db.commit()
            log.success(
                f"Лайк от пользователя ID {current_user.id} на твит ID {tweet_id} успешно поставлен."
            )
        except SQLAlchemyError as exc:
            await db.rollback()
            log.error(
                f"Ошибка БД при создании лайка ({current_user.id} -> {tweet_id}): {exc}",
                exc_info=True,
            )
            raise BadRequestError("Не удалось поставить лайк.") from exc

    async def unlike_tweet(
        self, db: AsyncSession, current_user: User, *, tweet_id: int
    ) -> None:
        """
        Убирает лайк с твита от имени текущего пользователя.

        Args:
            db (AsyncSession): Сессия БД.
            current_user (User): Пользователь, убирающий лайк.
            tweet_id (int): ID твита.

        Raises:
            NotFoundError: Если лайк для удаления не найден (твит не лайкнут этим пользователем).
            BadRequestError: При ошибке удаления лайка.
        """
        log.info(
            f"Пользователь ID {current_user.id} убирает лайк с твита ID {tweet_id}"
        )

        # Проверяем, существует ли лайк
        existing_like = await self.repo.get_like(
            db, user_id=current_user.id, tweet_id=tweet_id
        )

        if not existing_like:
            log.warning(
                f"Лайк от пользователя ID {current_user.id} на твит ID {tweet_id} не найден для удаления."
            )
            raise NotFoundError("Лайк не найден или уже удален.")

        try:
            await self.repo.delete_like(db, user_id=current_user.id, tweet_id=tweet_id)
            await db.commit()
            log.success(
                f"Лайк от пользователя ID {current_user.id} на твит ID {tweet_id} успешно удален."
            )
        except SQLAlchemyError as exc:
            await db.rollback()
            log.error(
                f"Ошибка БД при удалении лайка ({current_user.id} -> {tweet_id}): {exc}",
                exc_info=True,
            )
            raise BadRequestError("Не удалось убрать лайк.") from exc
