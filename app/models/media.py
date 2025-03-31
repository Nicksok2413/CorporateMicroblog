"""Модель для хранения информации о медиафайлах."""

from pathlib import Path

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.config import settings


class Media(Base):
    """Модель медиафайла с метаданными и связями.

    Attributes:
        id: Уникальный идентификатор
        user_id: ID пользователя, загрузившего файл
        filename: Имя файла в хранилище
    """

    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False, unique=True)

    # Связи
    user = relationship("User", back_populates="media")
    tweet_media = relationship(
        "TweetMedia",
        back_populates="media",
        cascade="all, delete-orphan"
    )

    @property
    def url(self) -> str:
        """Генерирует URL для доступа к файлу.

        Returns:
            str: Относительный URL вида /media/files/{filename}
        """
        return f"/media/files/{self.filename}"

    @property
    def path(self) -> Path:
        """Абсолютный путь к файлу в хранилище.

        Returns:
            Path: Полный путь к файлу
        """
        return Path(settings.STORAGE_PATH) / self.filename
