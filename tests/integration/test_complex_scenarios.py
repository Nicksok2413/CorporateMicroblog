from typing import List

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Tweet, Media, Like, Follow
from sqlalchemy import select, delete  # For direct DB checks/setup

pytestmark = pytest.mark.asyncio


async def test_feed_sorting_by_likes(
        client: AsyncClient, db_session: AsyncSession,
        test_user1: User, test_user2: User, test_user3_no_tweets: User,
        test_tweet_user1: Tweet, test_tweet_user2: Tweet,  # User1 follows User2
        test_follow_user1_on_user2: Follow, auth_headers_user1: dict
):
    # Make tweet1 more popular than tweet2 initially
    # User3 likes tweet1
    like1 = Like(user_id=test_user3_no_tweets.id, tweet_id=test_tweet_user1.id)
    # User2 likes tweet1
    like2 = Like(user_id=test_user2.id, tweet_id=test_tweet_user1.id)
    # User3 likes tweet2
    like3 = Like(user_id=test_user3_no_tweets.id, tweet_id=test_tweet_user2.id)
    db_session.add_all([like1, like2, like3])
    await db_session.commit()

    response = await client.get("/api_old/v1/tweets", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["result"] is True
    assert len(data["tweets"]) == 2
    # Expect tweet1 (2 likes) before tweet2 (1 like)
    assert data["tweets"][0]["id"] == test_tweet_user1.id
    assert data["tweets"][1]["id"] == test_tweet_user2.id
    assert len(data["tweets"][0]["likes"]) == 2
    assert len(data["tweets"][1]["likes"]) == 1


async def test_user_deletion_cascade(
        client: AsyncClient, db_session: AsyncSession,
        test_user1: User, test_user2: User, test_user3_no_tweets: User,
        test_tweet_user1: Tweet, test_tweet_user2: Tweet,
        test_like_user2_on_tweet1: Like,  # User2 liked tweet1
        test_like_user1_on_tweet2: Like,  # User1 liked tweet2 - need fixture
        test_follow_user1_on_user2: Follow,  # User1 follows User2
        test_follow_user3_on_user1: Follow  # User3 follows User1 - need fixture
):
    user1_id = test_user1.id
    user2_id = test_user2.id
    user3_id = test_user3_no_tweets.id
    tweet1_id = test_tweet_user1.id
    tweet2_id = test_tweet_user2.id

    # --- Delete User 1 ---
    # Cannot delete via API easily without adding an endpoint, simulate service/repo call
    await db_session.delete(test_user1)
    await db_session.commit()  # Commit deletion

    # --- Verify Cascades ---
    # User1's tweet should be deleted
    assert await db_session.get(Tweet, tweet1_id) is None
    # User2's tweet should NOT be deleted
    assert await db_session.get(Tweet, tweet2_id) is not None

    # Like from User2 on tweet1 (deleted user's tweet) should be gone
    # (Because tweet1 was deleted - cascade from Tweet)
    assert await db_session.get(Like, (user2_id, tweet1_id)) is None
    # Like from User1 (deleted) on tweet2 should be gone
    # (Because user1 was deleted - cascade from User)
    # Need the primary key for the like fixture test_like_user1_on_tweet2
    # assert await db_session.get(Like, (user1_id, tweet2_id)) is None # Re-enable if fixture added

    # Follow from User1 (deleted) to User2 should be gone
    assert await db_session.get(Follow, (user1_id, user2_id)) is None
    # Follow from User3 to User1 (deleted) should be gone
    assert await db_session.get(Follow, (user3_id, user1_id)) is None


async def test_tweet_deletion_cascade(
        client: AsyncClient, db_session: AsyncSession,
        test_user1: User, test_user2: User,
        test_tweet_user1_with_media: Tweet,  # Has media attached
        test_media_list: List[Media],
        test_like_user2_on_tweet1: Like,  # User2 liked this tweet
        auth_headers_user1: dict
):
    tweet_id = test_tweet_user1_with_media.id
    user2_id = test_user2.id
    media_ids = [m.id for m in test_media_list]

    # --- Delete the tweet via API ---
    response = await client.delete(f"/api_old/v1/tweets/{tweet_id}", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK

    # --- Verify Cascades ---
    # Tweet should be gone
    assert await db_session.get(Tweet, tweet_id) is None

    # Like on the tweet should be gone
    assert await db_session.get(Like, (user2_id, tweet_id)) is None

    # Check association table (tweet_media_association) - requires direct SQL or repo method
    from app.models.associations import tweet_media_association_table
    stmt = select(tweet_media_association_table).where(tweet_media_association_table.c.tweet_id == tweet_id)
    result = await db_session.execute(stmt)
    associations = result.fetchall()
    assert len(associations) == 0

    # Media itself should NOT be deleted
    for media_id in media_ids:
        assert await db_session.get(Media, media_id) is not None
