"""Seed data

Revision ID: ea2ce66c38d5
Revises: 29d1d504f832
Create Date: 2025-04-14 08:12:24.132416

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ea2ce66c38d5"
down_revision: Union[str, None] = "29d1d504f832"
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
    sa.column("tweet_id", sa.Integer),
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
    """Seed data."""
    # === Пользователи ===
    op.bulk_insert(
        users_table,
        [
            {"id": 1, "name": "Nick", "api_key": "test"},
            {"id": 2, "name": "Alice", "api_key": "alice_key"},
            {"id": 3, "name": "Bob", "api_key": "bob_key"},
            {"id": 4, "name": "Charlie", "api_key": "charlie_key"},
            {"id": 5, "name": "David (no tweets)", "api_key": "david_key"},
        ],
    )

    # === Твиты ===
    op.bulk_insert(
        tweets_table,
        [
            # Твиты Nick (ID=1)
            {"id": 1, "content": "Testing the new blog!", "author_id": 1},
            # Твиты Alice (ID=2)
            {"id": 2, "content": "Hello World! My first tweet!", "author_id": 2},
            {
                "id": 3,
                "content": "Enjoying the corporate life! #microblog",
                "author_id": 2,
            },
            {"id": 4, "content": "Check out this cool picture!", "author_id": 2},
            # Твиты Bob (ID=3)
            {"id": 5, "content": "Coding all day long...", "author_id": 3},
            {"id": 6, "content": "Just deployed a new feature.", "author_id": 3},
            # Твиты Charlie (ID=4)
            {"id": 7, "content": "Meeting marathon today.", "author_id": 4},
            {"id": 8, "content": "Thinking about weekend plans.", "author_id": 4},
            {"id": 9, "content": "Another picture.", "author_id": 4},
        ],
    )

    # === Медиа ===
    op.bulk_insert(
        media_table,
        [
            {
                "id": 1,
                "file_path": "1712730000000001_abcdef.gif",
                "tweet_id": 1,
            },  # Твит 1 Nick (ID=1) -> Медиа 1
            {
                "id": 2,
                "file_path": "1712730000000002_ghijkl.png",
                "tweet_id": 4,
            },  # Твит 4 Alice (ID=2) -> Медиа 2
            {
                "id": 3,
                "file_path": "1712730000000003_mnopqr.jpg",
                "tweet_id": 9,
            },  # Твит 9 Charlie (ID=4) -> Медиа 3
        ],
    )

    # === Лайки ===
    op.bulk_insert(
        likes_table,
        [
            # Nick (ID=1) лайкает твит Alice (ID=2)
            {"user_id": 1, "tweet_id": 3},
            # Alice (ID=2) лайкает твиты Nick (ID=1) и Bob (ID=3)
            {"user_id": 2, "tweet_id": 1},
            {"user_id": 2, "tweet_id": 6},
            # Bob (ID=3) лайкает твиты Nick (ID=1) и Alice (ID=2)
            {"user_id": 3, "tweet_id": 1},
            {"user_id": 3, "tweet_id": 2},
            {"user_id": 3, "tweet_id": 4},
            # Charlie (ID=4) лайкает твиты Alice (ID=2) и Bob (ID=3)
            {"user_id": 4, "tweet_id": 2},
            {"user_id": 4, "tweet_id": 5},
            {"user_id": 4, "tweet_id": 6},
        ],
    )

    # === Подписки ===
    op.bulk_insert(
        follows_table,
        [
            # Nick (ID=1) подписан на Alice (ID=2)
            {"follower_id": 1, "following_id": 2},
            # Alice (ID=2) подписана на Nick (ID=1), Bob (ID=3) и Charlie (ID=4)
            {"follower_id": 2, "following_id": 1},
            {"follower_id": 2, "following_id": 3},
            {"follower_id": 2, "following_id": 4},
            # Bob (ID=3) подписан на Nick (ID=1) и Alice (ID=2)
            {"follower_id": 3, "following_id": 1},
            {"follower_id": 3, "following_id": 2},
            # Charlie (ID=4) подписан на Alice (ID=2)
            {"follower_id": 4, "following_id": 2},
        ],
    )

    # Обновляем счетчик последовательности для таблицах tweets, users и media
    # Устанавливаем следующее значение = MAX(id) + 1
    # Используем pg_get_serial_sequence для надежности имени sequence
    op.execute(
        "SELECT setval(pg_get_serial_sequence('tweets', 'id'), "
        "COALESCE((SELECT MAX(id) FROM tweets), 1))"
    )
    op.execute(
        "SELECT setval(pg_get_serial_sequence('users', 'id'), "
        "COALESCE((SELECT MAX(id) FROM users), 1))"
    )
    op.execute(
        "SELECT setval(pg_get_serial_sequence('media', 'id'), "
        "COALESCE((SELECT MAX(id) FROM media), 1))"
    )
    # Примечание: COALESCE нужен на случай, если бы таблица была пуста (здесь не актуально, но это best practice)
    # setval без третьего аргумента или с 'true' установит ТЕКУЩЕЕ значение, т.е. следующее будет MAX + 1


def downgrade() -> None:
    """Remove seeded data."""
    # Удаляем в обратном порядке зависимостей
    op.execute(f"DELETE FROM {follows_table.name}")
    op.execute(f"DELETE FROM {likes_table.name}")
    op.execute(f"DELETE FROM {media_table.name}")
    op.execute(f"DELETE FROM {tweets_table.name}")
    op.execute(f"DELETE FROM {users_table.name}")
