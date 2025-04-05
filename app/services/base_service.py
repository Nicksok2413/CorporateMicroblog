"""Базовый класс для сервисов."""

from typing import Generic, TypeVar

from app.models.base import Base
from app.repositories.base import BaseRepository

# Определяем Generic типы
ModelType = TypeVar("ModelType", bound=Base)
RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepoType]):
    """
    Базовый сервис.

    Предоставляет доступ к ассоциированному репозиторию.
    Может содержать общую логику для всех сервисов, если такая появится.

    Args:
        repo (RepoType): Экземпляр репозитория, соответствующий модели сервиса.
    """

    def __init__(self, repo: RepoType):
        self.repo = repo
