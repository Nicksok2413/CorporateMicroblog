"""Сервисный слой для работы с твитами."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tweet import TweetRepository
from app.schemas.tweet import TweetCreate, TweetResponse


class TweetService:
    def __init__(self, db: AsyncSession):
        self.repo = TweetRepository(db)

    async def create_tweet(
            self,
            user_id: int,
            data: TweetCreate
    ) -> TweetResponse:
        """Создание твита с валидацией.

        Args:
            user_id: ID автора
            data: Данные твита

        Returns:
            TweetResponse: Созданный твит

        Raises:
            ValueError: Если медиа не найдены
        """
        # Валидация медиа (если есть)
        if data.tweet_media_ids:
            media = await self.repo.validate_media(data.tweet_media_ids)
            if len(media) != len(data.tweet_media_ids):
                raise ValueError("Некоторые медиа не найдены")

        tweet = await self.repo.create_tweet(user_id, data)
        return TweetResponse(
            id=tweet.id,
            content=tweet.content,
            author_id=tweet.author_id,
            likes_count=0,
            attachments=[]
        )
