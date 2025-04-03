"""
Скрипт для наполнения базы данных начальными данными.

Запускается ПОСЛЕ применения миграций Alembic.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Используем менеджер БД и модели/репозитории/сервисы
from app.core.database import Database
from app.core.logging import log
from app.models import Follow, Like, Media, Tweet, User
from app.repositories import (follow_repo, like_repo,
                              user_repo)

# Добавляем путь к проекту, чтобы можно было импортировать из app
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Данные для сидинга
SEED_USERS = [
    {"name": "Alice", "api_key": "alice_key_CHANGE_ME"},
    {"name": "Bob", "api_key": "bob_key_CHANGE_ME"},
    {"name": "Charlie", "api_key": "charlie_key_CHANGE_ME"},
]

# --- Важно: Локальный Database менеджер ---
# Создаем ОТДЕЛЬНЫЙ экземпляр Database для сидера,
# чтобы не конфликтовать с lifespan приложения, если оно запущено.
local_db = Database()


async def seed_data():
    """Основная асинхронная функция для выполнения сидинга."""
    log.info("Запуск сидинга базы данных...")

    # Подключаемся к БД
    try:
        # ВАЖНО: Если запускаете seed.py на хосте, а БД в Docker,
        # нужно либо пробросить порт (как у нас 5433), либо запускать seed внутри контейнера app.
        # Предполагаем запуск на хосте с проброшенным портом 5433 (если DB_HOST=db).
        # Если DB_HOST=localhost, то используем 5433.
        # Адаптируйте URL если нужно!
        # Мы используем settings.EFFECTIVE_DATABASE_URL, предполагая TESTING=False
        # Если DB_HOST='db', заменим на 'localhost:5433' для подключения с хоста.
        # seed_db_url = settings.EFFECTIVE_DATABASE_URL
        # if "@db:" in seed_db_url:
        #     log.warning("Обнаружен хост 'db', заменяем на 'localhost:5433' для сидера.")
        #     seed_db_url = seed_db_url.replace("@db:", "@localhost:5433/")

        # await local_db.connect(url=seed_db_url) # Подключаемся к БД с возможно переопределенным URL
        # ИЛИ Проще: Убедитесь, что POSTGRES_HOST/PORT в .env подходят для запуска сидера
        await local_db.connect()

    except Exception as e:
        log.critical(f"Не удалось подключиться к базе данных для сидинга: {e}", exc_info=True)
        return  # Прерываем выполнение

    async with local_db.session() as session:
        try:
            log.info("Начало транзакции сидинга...")

            # 1. Создание пользователей
            created_users = {}
            log.info(f"Создание {len(SEED_USERS)} пользователей...")
            for user_data in SEED_USERS:
                try:
                    # Проверка на существование (простая)
                    existing = await user_repo.get_by_api_key(session, api_key=user_data["api_key"])
                    if existing:
                        log.warning(f"Пользователь с ключом {user_data['api_key'][:4]}... уже существует, пропускаем.")
                        created_users[user_data["name"]] = existing
                        continue
                    # Создание через модель
                    user = User(**user_data)
                    session.add(user)
                    await session.flush()  # Получаем ID до коммита
                    await session.refresh(user)
                    log.success(f"Пользователь '{user.name}' (ID: {user.id}) добавлен.")
                    created_users[user.name] = user
                except IntegrityError:
                    await session.rollback()  # Откат только для этого пользователя
                    log.warning(f"Пользователь '{user_data['name']}' уже существует (ошибка целостности).")
                    # Попробуем получить его снова на всякий случай
                    user = await user_repo.get_by_api_key(session, api_key=user_data["api_key"])
                    if user:
                        created_users[user_data["name"]] = user
                    continue  # Пропускаем этого пользователя
                except Exception as e:
                    await session.rollback()
                    log.error(f"Не удалось создать пользователя '{user_data['name']}': {e}")
                    continue

            # Получаем ссылки на созданных пользователей
            alice = created_users.get("Alice")
            bob = created_users.get("Bob")
            charlie = created_users.get("Charlie")

            if not all([alice, bob, charlie]):
                log.error("Не удалось получить всех базовых пользователей для продолжения сидинга.")
                await session.rollback()  # Откатываем все изменения пользователей
                return

            # 2. Создание медиа (просто записи, без файлов)
            log.info("Создание записей медиа...")
            media_list = []
            try:
                for i in range(1, 4):
                    media_path = f"seed_image_{i}.jpg"
                    # Проверка на существование
                    existing_media = await session.execute(select(Media).where(Media.file_path == media_path))
                    if existing_media.scalars().first():
                        media_list.append(existing_media.scalars().first())
                        continue
                    media = Media(file_path=media_path)
                    session.add(media)
                await session.flush()  # Получаем ID
                # Обновляем список media_list реальными объектами из сессии
                stmt_media = select(Media).where(Media.file_path.like('seed_image_%'))
                res_media = await session.execute(stmt_media)
                media_list = list(res_media.scalars().all())  # Используем list
                log.success(f"Создано/Найдено {len(media_list)} записей медиа.")
            except Exception as e:
                await session.rollback()
                log.error(f"Ошибка при создании медиа: {e}")
                return

            # 3. Создание твитов
            log.info("Создание твитов...")
            tweets_map = {}
            try:
                tweet1_alice = Tweet(content="Привет! Это мой первый твит!", author_id=alice.id)
                # Прикрепляем медиа, если оно есть
                if media_list:
                    tweet1_alice.attachments.append(media_list[0])

                tweet2_bob = Tweet(content="Всем привет от Боба!", author_id=bob.id)

                tweet3_alice = Tweet(content="Думаю о работе...", author_id=alice.id)
                if len(media_list) > 1:
                    tweet3_alice.attachments.append(media_list[1])
                if len(media_list) > 2:
                    tweet3_alice.attachments.append(media_list[2])

                tweet4_charlie = Tweet(content="Просто проходил мимо.", author_id=charlie.id)

                tweets_to_add = [tweet1_alice, tweet2_bob, tweet3_alice, tweet4_charlie]
                session.add_all(tweets_to_add)
                await session.flush()  # Получаем ID
                # Обновляем для получения ID и связей
                for tweet in tweets_to_add:
                    await session.refresh(tweet, attribute_names=['attachments'])
                tweets_map = {t.id: t for t in tweets_to_add}
                log.success(f"Создано {len(tweets_to_add)} твитов.")
            except Exception as e:
                await session.rollback()
                log.error(f"Ошибка при создании твитов: {e}")
                return

            # 4. Создание подписок
            log.info("Создание подписок...")
            follows_to_add = [
                Follow(follower_id=alice.id, following_id=bob.id),  # Alice -> Bob
                Follow(follower_id=alice.id, following_id=charlie.id),  # Alice -> Charlie
                Follow(follower_id=bob.id, following_id=alice.id),  # Bob -> Alice
            ]
            try:
                # Простая проверка на дубликаты перед добавлением
                added_follows_count = 0
                for follow in follows_to_add:
                    existing_follow = await follow_repo.get_follow(session, follower_id=follow.follower_id,
                                                                   following_id=follow.following_id)
                    if not existing_follow:
                        session.add(follow)
                        added_follows_count += 1
                if added_follows_count > 0:
                    await session.flush()  # Добавляем только новые
                log.success(f"Добавлено {added_follows_count} новых подписок.")
            except Exception as e:
                await session.rollback()
                log.error(f"Ошибка при создании подписок: {e}")
                return

            # 5. Создание лайков
            log.info("Создание лайков...")
            if tweets_map:
                tweet_ids = list(tweets_map.keys())
                likes_data = [
                    {"user_id": alice.id, "tweet_id": tweet_ids[1]},  # Alice лайкает твит Боба
                    {"user_id": bob.id, "tweet_id": tweet_ids[0]},  # Bob лайкает 1й твит Alice
                    {"user_id": charlie.id, "tweet_id": tweet_ids[0]},  # Charlie лайкает 1й твит Alice
                    {"user_id": alice.id, "tweet_id": tweet_ids[2]},  # Alice лайкает свой 2й твит
                ]
                try:
                    added_likes_count = 0
                    for like_data in likes_data:
                        existing_like = await like_repo.get_like(session, user_id=like_data["user_id"],
                                                                 tweet_id=like_data["tweet_id"])
                        if not existing_like:
                            session.add(Like(**like_data))
                            added_likes_count += 1
                    if added_likes_count > 0:
                        await session.flush()
                    log.success(f"Добавлено {added_likes_count} новых лайков.")
                except Exception as e:
                    await session.rollback()
                    log.error(f"Ошибка при создании лайков: {e}")
                    return

            # Если все успешно, коммитим транзакцию
            await session.commit()
            log.success("Транзакция сидинга успешно закоммичена.")

        except Exception as e:
            # Ловим общие ошибки и откатываем всю транзакцию сидинга
            log.error(f"Произошла ошибка во время сидинга, транзакция отменена: {e}", exc_info=True)
            await session.rollback()
        finally:
            log.info("Сидинг базы данных завершен.")


async def main():
    """Главная точка входа для запуска сидера."""
    try:
        await seed_data()
    finally:
        # Гарантированно закрываем соединение с БД
        await local_db.disconnect()


if __name__ == "__main__":
    # Запускаем асинхронную функцию main
    log.info("Запуск скрипта сидинга...")
    asyncio.run(main())
    log.info("Скрипт сидинга завершил работу.")
