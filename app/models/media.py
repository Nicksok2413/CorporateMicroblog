"""Модель для хранения информации о медиафайлах."""

from sqlalchemy import Column, ForeignKey, Integer, String

from app.core.database import Base


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)

    @property
    def url(self) -> str:
        """Возвращает относительный URL файла."""
        return f"/media/files/{self.filename}"
