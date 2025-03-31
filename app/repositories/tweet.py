"""Репозиторий для работы с твитами в БД."""
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.tweet import Tweet
from app.schemas.tweet import TweetCreate


class TweetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tweet(self, user_id: int, data: TweetCreate) -> Tweet:
        """Создание твита в БД."""
        tweet = Tweet(
            content=data.tweet_data,
            author_id=user_id
        )
        self.db.add(tweet)
        await self.db.commit()
        return tweet

    async def validate_media(self, media_ids: List[int]) -> List[int]:
        """Проверка существования медиа."""
        result = await self.db.execute(
            select(Media.id).where(Media.id.in_(media_ids))
        return result.scalars().all()
