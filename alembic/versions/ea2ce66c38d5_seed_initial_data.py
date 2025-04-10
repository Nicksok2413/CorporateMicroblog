"""Seed initial data

Revision ID: ea2ce66c38d5
Revises: 4c36c7bb9d7e
Create Date: 2025-04-10 11:30:33.739696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ea2ce66c38d5'
down_revision: Union[str, None] = '4c36c7bb9d7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

users_table = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("api_key", sa.String),
)

tweets_table = sa.table(
    "tweets",
    sa.column("id", sa.Integer),
    sa.column("content", sa.String),
    sa.column("author_id", sa.Integer),
)

media_table = sa.table(
    "media",
    sa.column("id", sa.Integer),
    sa.column("file_path", sa.String),
)

tweet_media_association_table = sa.table(
    "tweet_media_association",
    sa.column("tweet_id", sa.Integer),
    sa.column("media_id", sa.Integer),
)

likes_table = sa.table(
    "likes",
    sa.column("user_id", sa.Integer),
    sa.column("tweet_id", sa.Integer),
)

follows_table = sa.table(
    "follows",
    sa.column("follower_id", sa.Integer),
    sa.column("following_id", sa.Integer),
)


def upgrade() -> None:
    """Seed data into tables."""
    # === Пользователи ===
    op.bulk_insert(users_table, [
        {'id': 1, 'test': 'Nick', 'api_key': 'test'},
        {'id': 2, 'name': 'Alice', 'api_key': 'alice_key'},
        {'id': 3, 'name': 'Bob', 'api_key': 'bob_key'},
        {'id': 4, 'name': 'Charlie', 'api_key': 'charlie_key'},
        {'id': 5, 'name': 'David (no tweets)', 'api_key': 'david_key'},
    ])

    # === Медиа (пример) ===
    # Предположим, что файлы с такими именами были бы загружены
    op.bulk_insert(media_table, [
        {'id': 1, 'file_path': '1712730000000000_abcdef.jpg'},
        {'id': 2, 'file_path': '1712730000000001_ghijkl.png'},
    ])

    # === Твиты ===
    op.bulk_insert(tweets_table, [
        # Твиты Alice (ID=2)
        {'id': 1, 'content': 'Hello World! My first tweet!', 'author_id': 2},
        {'id': 2, 'content': 'Enjoying the corporate life! #microblog', 'author_id': 2},
        {'id': 3, 'content': 'Check out this cool picture!', 'author_id': 2},  # Твит с картинкой

        # Твиты Bob (ID=3)
        {'id': 4, 'content': 'Coding all day long...', 'author_id': 3},
        {'id': 5, 'content': 'Just deployed a new feature.', 'author_id': 3},

        # Твиты Charlie (ID=4)
        {'id': 6, 'content': 'Meeting marathon today.', 'author_id': 4},
        {'id': 7, 'content': 'Thinking about weekend plans.', 'author_id': 4},
        {'id': 8, 'content': 'Another picture.', 'author_id': 4},  # Еще твит с картинкой
    ])

    # === Привязка медиа к твитам ===
    op.bulk_insert(tweet_media_association_table, [
        {'tweet_id': 3, 'media_id': 1},  # Твит 3 Alice -> Медиа 1
        {'tweet_id': 8, 'media_id': 2},  # Твит 8 Charlie -> Медиа 2
    ])

    # === Лайки ===
    op.bulk_insert(likes_table, [
        # Bob лайкает твиты Alice
        {'user_id': 3, 'tweet_id': 1},
        {'user_id': 3, 'tweet_id': 3},
        # Charlie лайкает твиты Alice и Bob
        {'user_id': 4, 'tweet_id': 1},
        {'user_id': 4, 'tweet_id': 4},
        {'user_id': 4, 'tweet_id': 5},
        # Alice лайкает твит Bob
        {'user_id': 2, 'tweet_id': 5},
    ])

    # === Подписки ===
    op.bulk_insert(follows_table, [
        # Alice подписана на Bob и Charlie
        {'follower_id': 2, 'following_id': 3},
        {'follower_id': 2, 'following_id': 4},
        # Bob подписан на Alice
        {'follower_id': 3, 'following_id': 2},
        # Charlie подписан на Alice
        {'follower_id': 4, 'following_id': 2},
    ])


def downgrade() -> None:
    """Remove seeded data."""
    # Удаляем в обратном порядке зависимостей
    op.execute(f"DELETE FROM {follows_table.name}")
    op.execute(f"DELETE FROM {likes_table.name}")
    op.execute(f"DELETE FROM {tweet_media_association_table.name}")
    op.execute(f"DELETE FROM {tweets_table.name}")
    op.execute(f"DELETE FROM {media_table.name}")
    op.execute(f"DELETE FROM {users_table.name}")
