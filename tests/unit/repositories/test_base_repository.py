from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.repositories.base import BaseRepository


# Создаем простую тестовую модель и схему
class MockModel(Base):  # Наследуемся от Base
    __tablename__ = "mock_items"
    # Определяем колонку id как Mapped и primary_key
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=False)  # autoincrement=False, т.к. мы будем задавать ID в тестах
    name: Mapped[str] = mapped_column(default="")  # Можно задать default


class MockCreateSchema(BaseModel):
    name: str


# Помечаем все тесты в этом модуле как асинхронные
pytestmark = pytest.mark.asyncio


# Фикстура для создания экземпляра репозитория
@pytest.fixture
def base_repo() -> BaseRepository[MockModel, MockCreateSchema]:
    return BaseRepository(model=MockModel)


# --- Тесты для get ---

async def test_base_repo_get_found(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест get, когда объект найден."""
    mock_result = MagicMock()
    mock_instance = MockModel(id=1, name="Test")
    mock_result.scalars.return_value.first.return_value = mock_instance
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    found_obj = await base_repo.get(mock_db_session, obj_id=1)

    assert found_obj == mock_instance

    # Проверяем, что execute был вызван с правильным select
    assert mock_db_session.execute.await_args[0][0].compare(
        select(MockModel).where(MockModel.id == 1)
    )


async def test_base_repo_get_not_found(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест get, когда объект не найден."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None  # Не найден
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    found_obj = await base_repo.get(mock_db_session, obj_id=1)

    assert found_obj is None

    # Проверяем вызов execute
    assert mock_db_session.execute.await_args[0][0].compare(
        select(MockModel).where(MockModel.id == 1)
    )


# --- Тесты для get_all ---
async def test_base_repo_get_all(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест получения всех объектов."""
    mock_result = MagicMock()
    mock_instances = [MockModel(id=1, name="Test1"), MockModel(id=2, name="Test2")]
    mock_result.scalars.return_value.all.return_value = mock_instances
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Запускаем метод
    all_objs = await base_repo.get_all(mock_db_session)

    assert all_objs == mock_instances

    # Проверяем вызов execute с правильным select
    assert mock_db_session.execute.await_args[0][0].compare(select(MockModel))


# --- Тесты для add ---
async def test_base_repo_add(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест добавления объекта в сессию."""
    obj_to_add = MockModel(id=3, name="New Item")

    # Запускаем метод
    added_obj = await base_repo.add(mock_db_session, db_obj=obj_to_add)

    assert added_obj == obj_to_add
    mock_db_session.add.assert_called_once_with(obj_to_add)


# --- Тесты для create ---
# create уже хорошо покрыт тестами сервисов

# --- Тесты для delete ---
async def test_base_repo_delete(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест пометки объекта на удаление."""
    obj_to_delete = MockModel(id=4, name="Delete Me")
    mock_db_session.delete = AsyncMock()  # Убедимся, что есть AsyncMock

    # Запускаем метод
    await base_repo.delete(mock_db_session, db_obj=obj_to_delete)

    mock_db_session.delete.assert_awaited_once_with(obj_to_delete)


# --- Тесты для remove ---
async def test_base_repo_remove_found(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест remove, когда объект найден."""
    obj_to_remove_id = 5
    obj_instance = MockModel(id=obj_to_remove_id, name="Remove Me")

    # Мокируем get и delete
    mock_result_get = MagicMock()
    mock_result_get.scalars.return_value.first.return_value = obj_instance
    mock_db_session.execute = AsyncMock(return_value=mock_result_get)
    mock_db_session.delete = AsyncMock()

    # Запускаем метод
    removed_obj = await base_repo.remove(mock_db_session, obj_id=obj_to_remove_id)

    assert removed_obj == obj_instance

    # Проверяем вызов get
    assert mock_db_session.execute.await_args[0][0].compare(
        select(MockModel).where(MockModel.id == obj_to_remove_id)
    )

    # Проверяем вызов delete
    mock_db_session.delete.assert_awaited_once_with(obj_instance)


async def test_base_repo_remove_not_found(
        base_repo: BaseRepository,
        mock_db_session: MagicMock,
):
    """Тест remove, когда объект не найден."""
    obj_to_remove_id = 6

    # Мокируем get (объект не найден)
    mock_result_get = MagicMock()
    mock_result_get.scalars.return_value.first.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result_get)
    mock_db_session.delete = AsyncMock()

    # Запускаем метод
    removed_obj = await base_repo.remove(mock_db_session, obj_id=obj_to_remove_id)

    assert removed_obj is None

    # Проверяем вызов get
    assert mock_db_session.execute.await_args[0][0].compare(
        select(MockModel).where(MockModel.id == obj_to_remove_id)
    )

    # Delete не должен вызываться
    mock_db_session.delete.assert_not_awaited()
