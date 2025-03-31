"""Репозиторий для работы с медиафайлами в БД."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media


class MediaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

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
        self.db.add(media)
        await self.db.commit()
        return media
