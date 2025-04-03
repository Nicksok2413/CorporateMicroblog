import asyncio
from typing import AsyncGenerator, Generator, List

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db_session
from app.main import app
from app.models import User, Tweet, Media, Follow, Like

# --- Базовые фикстуры (как в предыдущем ответе) ---
test_engine = create_async_engine(settings.EFFECTIVE_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession,
                                         expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Можно раскомментировать для удаления после всех тестов
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        # Важно откатывать изменения после каждого теста для изоляции
        await session.rollback()
        await session.close()  # Закрываем сессию


@pytest.fixture(scope="session")
def event_loop(request) -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            # Явное закрытие не нужно, т.к. db_session - контекстный менеджер
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(app=app, base_url="http://testserver") as test_client:  # Убрал /api_old/v1 из base_url
        yield test_client
    app.dependency_overrides.clear()


# --- Фикстуры данных ---
@pytest_asyncio.fixture(scope="function")
async def test_user1(db_session: AsyncSession) -> User:
    user = User(name="Test User 1", api_key="testkey1")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user2(db_session: AsyncSession) -> User:
    user = User(name="Test User 2", api_key="testkey2")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user3_no_tweets(db_session: AsyncSession) -> User:
    user = User(name="Test User 3", api_key="testkey3")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_media(db_session: AsyncSession) -> Media:
    media = Media(file_path="test_image.jpg")
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)
    return media


@pytest_asyncio.fixture(scope="function")
async def test_media_list(db_session: AsyncSession) -> List[Media]:
    media1 = Media(file_path="image1.png")
    media2 = Media(file_path="image2.gif")
    db_session.add_all([media1, media2])
    await db_session.commit()
    await db_session.refresh(media1)
    await db_session.refresh(media2)
    return [media1, media2]


@pytest_asyncio.fixture(scope="function")
async def test_tweet_user1(db_session: AsyncSession, test_user1: User) -> Tweet:
    tweet = Tweet(content="Tweet from User 1", author_id=test_user1.id)
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    return tweet


@pytest_asyncio.fixture(scope="function")
async def test_tweet_user2(db_session: AsyncSession, test_user2: User) -> Tweet:
    tweet = Tweet(content="Tweet from User 2", author_id=test_user2.id)
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    return tweet


@pytest_asyncio.fixture(scope="function")
async def test_tweet_user1_with_media(db_session: AsyncSession, test_user1: User,
                                      test_media_list: List[Media]) -> Tweet:
    tweet = Tweet(content="Tweet from User 1 with media", author_id=test_user1.id)
    tweet.attachments.extend(test_media_list)
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet, attribute_names=['attachments'])
    return tweet


@pytest_asyncio.fixture(scope="function")
async def test_like_user2_on_tweet1(db_session: AsyncSession, test_user2: User, test_tweet_user1: Tweet) -> Like:
    like = Like(user_id=test_user2.id, tweet_id=test_tweet_user1.id)
    db_session.add(like)
    await db_session.commit()
    # refresh не нужен для Like, т.к. нет генерируемых полей
    return like


@pytest_asyncio.fixture(scope="function")
async def test_follow_user1_on_user2(db_session: AsyncSession, test_user1: User, test_user2: User) -> Follow:
    follow = Follow(follower_id=test_user1.id, following_id=test_user2.id)
    db_session.add(follow)
    await db_session.commit()
    return follow


@pytest_asyncio.fixture(scope="function")
async def auth_headers_user1(test_user1: User) -> dict:
    return {"api-key": test_user1.api_key}


@pytest_asyncio.fixture(scope="function")
async def auth_headers_user2(test_user2: User) -> dict:
    return {"api-key": test_user2.api_key}
