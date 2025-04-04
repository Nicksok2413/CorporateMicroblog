"""Сервис для управления подписками."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (BadRequestError, ConflictError,
                                 PermissionDeniedError, NotFoundError)
from app.core.logging import log
from app.models import User
from app.repositories import follow_repo, user_repo


class FollowService:
    """
    Сервис для бизнес-логики, связанной с подписками.

    Не наследуется от BaseService, так как работает с репозиторием Follow,
    но основная логика связана с проверкой Users.
    """

    def __init__(self, repo: type(follow_repo), user_repository: type(user_repo)):
        self.repo = repo
        self.user_repo = user_repository

    async def _validate_follow_action(self, db: AsyncSession, follower_id: int, following_id: int) -> User:
        """
        Проверяет возможность подписки/отписки.

        - Пользователь не может подписываться/отписываться от себя.
        - Целевой пользователь должен существовать.

        Args:
            db: Сессия БД.
            follower_id: ID пользователя, выполняющего действие.
            following_id: ID целевого пользователя.

        Returns:
            User: Объект целевого пользователя (на кого подписываются/отписываются).

        Raises:
            ForbiddenException: Если пользователь пытается подписаться на себя.
            NotFoundError: Если целевой пользователь не найден.
        """
        if follower_id == following_id:
            log.warning(f"Пользователь ID {follower_id} пытается подписаться/отписаться от себя.")
            raise PermissionDeniedError("Вы не можете подписаться на себя.")

        # Проверяем, существует ли пользователь, на которого подписываемся
        user_to_follow = await self.user_repo.get(db, obj_id=following_id)

        if not user_to_follow:
            log.warning(f"Пользователь ID {following_id} (на которого пытаются подписаться/отписаться) не найден.")
            raise NotFoundError(f"Пользователь с ID {following_id} не найден.")
        return user_to_follow

    async def follow_user(self, db: AsyncSession, *, current_user: User, user_to_follow_id: int):
        """
        Осуществляет подписку одного пользователя на другого.

        Args:
            db: Сессия БД.
            current_user: Пользователь, который подписывается.
            user_to_follow_id: ID пользователя, на которого нужно подписаться.

        Raises:
            ForbiddenException: Если пользователь пытается подписаться на себя.
            NotFoundError: Если целевой пользователь не найден.
            ConflictException: Если подписка уже существует.
            BadRequestError: При ошибке сохранения.
        """
        follower_id = current_user.id
        log.info(f"Пользователь ID {follower_id} пытается подписаться на пользователя ID {user_to_follow_id}")
        await self._validate_follow_action(db, follower_id, user_to_follow_id)

        # Проверяем, не подписан ли уже
        existing_follow = await self.repo.get_follow(db, follower_id=follower_id, following_id=user_to_follow_id)

        if existing_follow:
            log.warning(f"Пользователь ID {follower_id} уже подписан на пользователя ID {user_to_follow_id}.")
            raise ConflictError("Вы уже подписаны на этого пользователя.")

        try:
            await self.repo.create_follow(db, follower_id=follower_id, following_id=user_to_follow_id)
            log.success(f"Пользователь ID {follower_id} успешно подписался на пользователя ID {user_to_follow_id}")
        except IntegrityError as exc:
            # На случай гонки запросов или если проверка выше не сработала
            log.warning(f"Конфликт целостности при подписке ({follower_id} -> {user_to_follow_id}): {exc}")
            raise ConflictError("Не удалось подписаться (возможно, подписка уже существует).") from exc
        except Exception as exc:
            log.error(f"Ошибка при создании подписки ({follower_id} -> {user_to_follow_id}): {exc}", exc_info=True)
            raise BadRequestError("Не удалось подписаться на пользователя.") from exc

    async def unfollow_user(self, db: AsyncSession, *, current_user: User, user_to_unfollow_id: int):
        """
        Осуществляет отписку одного пользователя от другого.

        Args:
            db: Сессия БД.
            current_user: Пользователь, который отписывается.
            user_to_unfollow_id: ID пользователя, от которого нужно отписаться.

        Raises:
            ForbiddenException: Если пользователь пытается отписаться от себя.
            NotFoundError: Если целевой пользователь не найден или подписки не существует.
            BadRequestError: При ошибке удаления.
        """
        follower_id = current_user.id
        log.info(f"Пользователь ID {follower_id} пытается отписаться от пользователя ID {user_to_unfollow_id}")
        await self._validate_follow_action(db, follower_id, user_to_unfollow_id)

        removed = await self.repo.remove_follow(db, follower_id=follower_id, following_id=user_to_unfollow_id)

        if not removed:
            log.warning(f"Подписка пользователя ID {follower_id} на пользователя ID {user_to_unfollow_id} не найдена для удаления.")
            raise NotFoundError("Вы не подписаны на этого пользователя.")
        log.success(f"Пользователь ID {follower_id} успешно отписался от пользователя ID {user_to_unfollow_id}")


# Создаем экземпляр сервиса
follow_service = FollowService(follow_repo, user_repo)  # Передаем оба репозитория
