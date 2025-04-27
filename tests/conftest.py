from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir

import pytest

from src.core.config import settings
from src.models import Follow, Like, Media, Tweet, User

# Убедимся, что настройки загружены с TESTING=True
assert settings.TESTING, "Тесты должны запускаться с TESTING=True"


# --- Фикстура для автоматической очистки временных папок ---
# Используем scope="session", чтобы выполнилось один раз после всех тестов
# autouse=True означает, что фикстура будет использоваться автоматически без явного запроса
@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_dirs(request):
    """Очищает временные директории для медиа и логов после завершения сессии тестов."""
    # Код до yield выполнится перед началом сессии (здесь не нужен)
    yield
    # Код после yield выполнится после завершения сессии
    print("\nОчистка временных директорий после тестов...")

    temp_media_path = Path(gettempdir()) / "temp_media"
    temp_log_path = Path(gettempdir()) / "temp_logs"

    deleted_count = 0
    errors = []

    for temp_path in [temp_media_path, temp_log_path]:
        if temp_path.exists() and temp_path.is_dir():
            try:
                # Используем shutil.rmtree для рекурсивного удаления директории и ее содержимого
                rmtree(temp_path)
                print(f"Успешно удалена директория: {temp_path}")
                deleted_count += 1
            except OSError as exc:
                error_msg = f"Ошибка при удалении директории {temp_path}: {exc}"
                print(error_msg)
                errors.append(error_msg)
        else:
            print(f"Директория для очистки не найдена: {temp_path}")

    if errors:
        print(f"Завершено с ошибками при очистке: {errors}")
    else:
        print(f"Очистка временных директорий завершена ({deleted_count} удалено).")


# --- Фикстуры для базовых объектов моделей ---


# Фикстура пользователя `Test User`
@pytest.fixture
def test_user_obj() -> User:
    return User(
        id=1,
        name="Test User",
        api_key_hash="$argon2id$v=19$m=65536,t=3,p=4$somesalt$somehash",  # Пример хеша
        api_key_sha256="a" * 64,  # Пример SHA256
    )


# Фикстура пользователя `Test Alice`
@pytest.fixture
def test_alice_obj() -> User:
    return User(
        id=2,
        name="Test Alice",
        api_key_hash="$argon2id$v=19$m=65536,t=3,p=4$othersalt$otherhash",
        api_key_sha256="b" * 64,
    )


# Фикстура пользователя `Test Bob`
@pytest.fixture
def test_bob_obj() -> User:
    return User(
        id=3,
        name="Test Bob",
        api_key_hash="$argon2id$v=19$m=65536,t=3,p=4$anothersalt$anotherhash",
        api_key_sha256="c" * 64,
    )


# Фикстура твита
@pytest.fixture
def test_tweet_obj() -> Tweet:
    # Создаем с минимально необходимыми полями для тестов
    tweet = Tweet(id=101, content="Test Tweet Content", author_id=1)
    # Имитируем пустые связи, если тест не мокирует их загрузку
    tweet.attachments = []
    tweet.likes = []
    return tweet


# Фикстура медиа
@pytest.fixture
def test_media_obj() -> Media:
    # tweet_id=None по умолчанию, пока не привязан
    return Media(id=201, file_path="test/path/image.jpg", tweet_id=None)


# Фикстура лайка
@pytest.fixture
def test_like_obj() -> Like:
    return Like(user_id=1, tweet_id=101)


# Фикстура подписки
@pytest.fixture
def test_follow_obj() -> Follow:
    return Follow(follower_id=1, following_id=2)
