"""Репозиторий для работы с твитами в БД."""
from typing import List

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.like import Like
from app.models.media import Media
from app.models.tweet import Tweet
from app.models.user import User
from app.schemas.tweet import TweetCreate


class TweetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_tweet(self, user_id: int, data: TweetCreate) -> Tweet:
        """Создание твита в БД."""
        tweet = Tweet(
            content=data.tweet_data,
            author_id=user_id
        )
        self.session.add(tweet)
        await self.session.commit()
        return tweet

    async def validate_media(self, media_ids: List[int]) -> List[int]:
        """Проверка существования медиа."""
        result = await self.session.execute(
            select(Media.id).where(Media.id.in_(media_ids))
        )
        return result.scalars().all()

    async def get_feed_tweets(
            self,
            user_id: int,
            limit: int = 50,
            offset: int = 0
    ) -> list[tuple[Tweet, int]]:
        """Получает ленту твитов для пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество твитов
            offset: Смещение

        Returns:
            list: Список кортежей (твит, количество лайков)
        """
        # Подзапрос для получения ID подписок
        following_subquery = select(Follow.followed_id).filter_by(follower_id=user_id).subquery()

        query = (
            select(
                Tweet,
                func.count(Like.user_id).label("likes_count")
            )
            .join(User, Tweet.author_id == User.id)
            .outerjoin(Like, Tweet.id == Like.tweet_id)
            .where(
                or_(
                    Tweet.author_id == user_id,
                    Tweet.author_id.in_(following_subquery)
                )
            )
            .group_by(Tweet.id)
            .order_by(desc("likes_count"))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return result.all()
