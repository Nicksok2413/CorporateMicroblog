# tests/unit/test_repositories.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import tweet_repo, user_repo  # Import repos
from app.models import Tweet, User  # Import models

pytestmark = pytest.mark.asyncio


# --- Test TweetRepository ---

async def test_get_feed_repo_empty_authors(db_session: AsyncSession):
    tweets = await tweet_repo.get_feed_for_user(db=db_session, author_ids=[])
    assert tweets == []


async def test_get_feed_repo_nonexistent_authors(db_session: AsyncSession):
    tweets = await tweet_repo.get_feed_for_user(db=db_session, author_ids=[998, 999])
    assert tweets == []


# --- Test UserRepository ---

async def test_get_by_api_key_repo_none(db_session: AsyncSession):
    user = await user_repo.get_by_api_key(db=db_session, api_key=None)  # type: ignore
    assert user is None


async def test_get_by_api_key_repo_empty_string(db_session: AsyncSession):
    user = await user_repo.get_by_api_key(db=db_session, api_key="")
    assert user is None

# Add more direct repository tests if specific logic needs isolation
