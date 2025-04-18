from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError  # Для имитации ошибок БД

from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.models import Follow, User
from src.services.follow_service import FollowService

# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для создания экземпляра сервиса
@pytest.fixture
def follow_service(
        mock_follow_repo: MagicMock,
        mock_user_repo: MagicMock
) -> FollowService:
    service = FollowService(repo=mock_follow_repo, user_repo=mock_user_repo)
    return service


# --- Тесты для _validate_follow_action ---

async def test_validate_follow_action_success(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        mock_user_repo: MagicMock,
):
    """Тест успешной валидации (не себя, цель существует)."""
    # Настраиваем мок
    mock_user_repo.get.return_value = test_alice_obj

    # Вызываем метод сервиса
    target_user = await follow_service._validate_follow_action(
        db=mock_db_session,
        follower_id=test_user_obj.id,
        following_id=test_alice_obj.id
    )

    assert target_user == test_alice_obj
    mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=test_alice_obj.id)


async def test_validate_follow_action_self_follow(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_user_repo: MagicMock,
):
    """Тест валидации при попытке подписаться/отписаться от себя."""
    # Проверяем, что выбрасывается PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await follow_service._validate_follow_action(
            db=mock_db_session,
            follower_id=test_user_obj.id,
            following_id=test_user_obj.id
        )

    assert "Вы не можете подписаться на себя" in str(exc_info.value)
    mock_user_repo.get.assert_not_awaited()


async def test_validate_follow_action_target_not_found(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_user_repo: MagicMock,
):
    """Тест валидации, когда целевой пользователь не найден."""
    target_id = 999
    # Настраиваем мок
    mock_user_repo.get.return_value = None  # Цель не найдена

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError) as exc_info:
        await follow_service._validate_follow_action(
            db=mock_db_session,
            follower_id=test_user_obj.id,
            following_id=target_id
        )

    assert f"Пользователь с ID {target_id} не найден" in str(exc_info.value)
    mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=target_id)


# --- Тесты для follow_user ---

async def test_follow_user_success(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест успешной подписки."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj  # Цель найдена
    mock_follow_repo.get_follow.return_value = None  # Еще не подписан
    mock_follow_repo.add_follow.return_value = None

    # Вызываем метод сервиса
    await follow_service.follow_user(
        db=mock_db_session, current_user=test_user_obj, user_to_follow_id=test_alice_obj.id
    )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once_with(mock_db_session, obj_id=test_alice_obj.id)
    mock_follow_repo.get_follow.assert_awaited_once_with(mock_db_session, follower_id=test_user_obj.id,
                                                         following_id=test_alice_obj.id)
    mock_follow_repo.add_follow.assert_awaited_once_with(mock_db_session, follower_id=test_user_obj.id,
                                                         following_id=test_alice_obj.id)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_follow_user_validation_fails(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        mock_follow_repo: MagicMock,
):
    """Тест подписки, когда валидация не проходит (на себя)."""
    # Используем ID текущего пользователя как цель
    # Проверяем, что выбрасывается PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        await follow_service.follow_user(
            db=mock_db_session, current_user=test_user_obj, user_to_follow_id=test_user_obj.id
        )

    # Проверяем, что другие методы не вызывались
    mock_follow_repo.get_follow.assert_not_awaited()
    mock_follow_repo.add_follow.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()


async def test_follow_user_already_following(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        test_follow_obj: Follow,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест попытки подписаться на пользователя, на которого уже подписан."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj
    # Имитируем, что подписка уже есть
    mock_follow_repo.get_follow.return_value = test_follow_obj

    # Проверяем, что выбрасывается ConflictError
    with pytest.raises(ConflictError):
        await follow_service.follow_user(
            db=mock_db_session, current_user=test_user_obj, user_to_follow_id=test_alice_obj.id
        )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once()
    mock_follow_repo.get_follow.assert_awaited_once()
    # Проверяем, что другие методы не вызывались
    mock_follow_repo.add_follow.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_follow_user_db_error(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест ошибки БД при добавлении подписки."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj
    mock_follow_repo.get_follow.return_value = None
    # Имитируем ошибку БД
    mock_follow_repo.add_follow.side_effect = SQLAlchemyError("DB insert error")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await follow_service.follow_user(
            db=mock_db_session, current_user=test_user_obj, user_to_follow_id=test_alice_obj.id
        )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once()
    mock_follow_repo.get_follow.assert_awaited_once()
    mock_follow_repo.add_follow.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


async def test_follow_user_db_integrity_error(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест ошибки IntegrityError при добавлении подписки."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj
    mock_follow_repo.get_follow.return_value = None
    # Имитируем ошибку IntegrityError (например, гонка или проблема с constraint)
    mock_follow_repo.add_follow.side_effect = IntegrityError("Constraint violation", params=(), orig=None)

    # Проверяем, что выбрасывается ConflictError (сервис обрабатывает IntegrityError как конфликт)
    with pytest.raises(ConflictError):
        await follow_service.follow_user(
            db=mock_db_session, current_user=test_user_obj, user_to_follow_id=test_alice_obj.id
        )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once()
    mock_follow_repo.get_follow.assert_awaited_once()
    mock_follow_repo.add_follow.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк


# --- Тесты для unfollow_user ---

async def test_unfollow_user_success(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        test_follow_obj: Follow,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест успешной отписки."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj
    # Имитируем, что подписка существует
    mock_follow_repo.get_follow.return_value = test_follow_obj
    mock_follow_repo.delete_follow.return_value = None

    # Вызываем метод сервиса
    await follow_service.unfollow_user(
        db=mock_db_session, current_user=test_user_obj, user_to_unfollow_id=test_alice_obj.id
    )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once()
    mock_follow_repo.get_follow.assert_awaited_once()
    mock_follow_repo.delete_follow.assert_awaited_once_with(mock_db_session,
                                                            follower_id=test_user_obj.id,
                                                            following_id=test_alice_obj.id)
    mock_db_session.commit.assert_awaited_once()  # Должен быть коммит
    mock_db_session.rollback.assert_not_awaited()  # Роллбэка быть не должно


async def test_unfollow_user_not_following(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест отписки от пользователя, на которого не подписан."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj
    # Имитируем, что подписки нет
    mock_follow_repo.get_follow.return_value = None

    # Проверяем, что выбрасывается NotFoundError
    with pytest.raises(NotFoundError):
        await follow_service.unfollow_user(
            db=mock_db_session, current_user=test_user_obj, user_to_unfollow_id=test_alice_obj.id
        )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once()
    mock_follow_repo.get_follow.assert_awaited_once()
    # Проверяем, что другие методы не вызывались
    mock_follow_repo.delete_follow.assert_not_awaited()
    mock_db_session.commit.assert_not_awaited()
    mock_db_session.rollback.assert_not_awaited()


async def test_unfollow_user_db_error(
        follow_service: FollowService,
        mock_db_session: MagicMock,
        test_user_obj: User,
        test_alice_obj: User,
        test_follow_obj: Follow,
        mock_user_repo: MagicMock,
        mock_follow_repo: MagicMock,
):
    """Тест ошибки БД при удалении подписки."""
    # Настраиваем моки
    mock_user_repo.get.return_value = test_alice_obj
    mock_follow_repo.get_follow.return_value = test_follow_obj
    # Имитируем ошибку БД
    mock_follow_repo.delete_follow.side_effect = SQLAlchemyError("DB delete error")

    # Проверяем, что выбрасывается BadRequestError
    with pytest.raises(BadRequestError):
        await follow_service.unfollow_user(
            db=mock_db_session, current_user=test_user_obj, user_to_unfollow_id=test_alice_obj.id
        )

    # Проверяем вызовы
    mock_user_repo.get.assert_awaited_once()
    mock_follow_repo.get_follow.assert_awaited_once()
    mock_follow_repo.delete_follow.assert_awaited_once()
    mock_db_session.commit.assert_not_awaited()  # Коммита быть не должно
    mock_db_session.rollback.assert_awaited_once()  # Должен быть роллбэк
