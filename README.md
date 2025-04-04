# Сервис Микроблогов (Бэкенд)

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/database-PostgreSQL-blue.svg)](https://www.postgresql.org/)

Бэкенд для корпоративного сервиса микроблогов, реализованный на Python с использованием FastAPI, SQLAlchemy и PostgreSQL.

## Легенда

Вы — главный бэкенд-разработчик на Python, отвечающий за реализацию бэкенда для нового корпоративного сервиса микроблогов, похожего на Twitter. Вам предоставлено техническое задание и готовый фронтенд с описанием API. Ваша задача — реализовать бэкенд, соответствующий требованиям.

## Функциональные Требования

*   [x] Пользователь может добавить новый твит.
*   [x] Пользователь может удалить свой твит.
*   [x] Пользователь может зафоловить другого пользователя.
*   [x] Пользователь может отписаться от другого пользователя.
*   [x] Пользователь может отмечать твит как понравившийся (лайк).
*   [x] Пользователь может убрать отметку «Нравится» (анлайк).
*   [x] Пользователь может получить ленту из твитов пользователей, которых он фоловит (отсортированных по популярности).
*   [x] Твит может содержать картинку(и).
*   [x] Пользователь может получить информацию о своём профиле (`/users/me`).
*   [x] Пользователь может получить информацию о произвольном профиле по его ID (`/users/{id}`).

## Нефункциональные Требования

*   [x] Простое развертывание через Docker Compose.
*   [x] Данные не теряются между перезапусками (используются Docker volumes).
*   [x] API задокументировано через Swagger UI и ReDoc (автоматически генерируется FastAPI).
*   [x] Код покрыт unit-тестами (необходимо реализовать).
*   [x] Код проверен линтером (Ruff) и статическим анализатором типов (MyPy).

## Технологический Стек

*   **Язык:** Python 3.12+
*   **Фреймворк:** FastAPI
*   **База данных:** PostgreSQL 15+
*   **ORM:** SQLAlchemy 2.0+ (asyncio)
*   **Миграции БД:** Alembic
*   **Валидация данных:** Pydantic V2
*   **Асинхронный драйвер БД:** asyncpg
*   **Логирование:** Loguru
*   **Тестирование:** Pytest, pytest-asyncio, httpx
*   **Линтинг/Форматирование:** Ruff
*   **Типизация:** MyPy
*   **Контейнеризация:** Docker, Docker Compose
*   **ASGI сервер:** Uvicorn

## Структура Проекта
```
microblog/
    ├── .env.example                  # Шаблон конфигурации
    ├── .gitignore                    # Игнорируемые файлы
    ├── alembic.ini                   # Настройки миграций
    ├── docker-compose.yml            # Композиция сервисов
    ├── Dockerfile                    # Образ приложения
    ├── pytest.ini                    # Настройки тестирования
    ├── README.md                     # Документация
    ├── requirements.txt              # Зависимости (Production)
    ├── requirements-dev.txt          # Зависимости (Development)
    │
    ├── app/                          # Основное приложение
    │   ├── __init__.py
    │   ├── main.py                   # Точка входа в приложение
    │   │
    │   ├── api/                      # API (роуты, зависимости)
    │   │   ├── __init__.py
    │   │   ├── router.py             # Агрегация API роутеров
    │   │   └── v1/                   # Версия API
    │   │       ├── __init__.py
    │   │       ├── dependencies.py   # Зависимости
    │   │       ├── router.py         # Агрегация роутеров для API версии v1
    │   │       └── routes/           # Маршруты
    │   │         ├── __init__.py
    │   │         ├── users.py        # /users/...
    │   │         ├── tweets.py       # /tweets/...
    │   │         ├── media.py        # /media
    │   │         ├── likes.py        # /tweets/{tweet_id}/likes
    │   │         └── follow.py       # /users/{user_id}/follow
    │   │
    │   ├── core/                     # Ядро приложения
    │   │   ├── __init__.py
    │   │   ├── config.py             # Настройки приложения
    │   │   ├── database.py           # Подключение к БД
    │   │   ├── exceptions.py         # Обработка исключений
    │   │   └── logging.py            # Настройка логгера
    │   │
    │   ├── models/                   # SQLAlchemy модели
    │   │   ├── __init__.py
    │   │   ├── associations.py       # Модели ассоциативных таблиц
    │   │   ├── base.py               # Базовая модель
    │   │   ├── user.py               # Модель для User
    │   │   ├── tweet.py              # Модель для Tweet
    │   │   ├── media.py              # Модель для media
    │   │   ├── like.py               # Модель для like
    │   │   └── follow.py             # Модель для follow
    │   │
    │   ├── repositories/             # Логика работы с базой данных (CRUD)
    │   │   ├── __init__.py
    │   │   ├── base.py               # Базовый репозиторий
    │   │   ├── user.py               # Репозиторий для User
    │   │   ├── tweet.py              # Репозиторий для Tweet
    │   │   ├── media.py              # Репозиторий для media
    │   │   ├── like.py               # Репозиторий для like
    │   │   └── follow.py             # Репозиторий для follow
    │   │
    │   ├── schemas/                  # Pydantic схемы
    │   │   ├── __init__.py
    │   │   ├── base.py               # Базовая схема
    │   │   ├── user.py               # Схема для User
    │   │   ├── tweet.py              # Схема для Tweet
    │   │   ├── media.py              # Схема для media
    │   │   ├── like.py               # Схема для like
    │   │   └── follow.py             # Схема для follow
    │   │
    │   ├── services/                 # Бизнес-логика
    │   │   ├── __init__.py
    │   │   ├── base_service.py
    │   │   ├── user_service.py
    │   │   ├── tweet_service.py
    │   │   ├── media_service.py
    │   │   ├── like_service.py
    │   │   └── follow_service.py
    │   │
    │   └── static/                   # Статические файлы
    │       ├── index.html
    │       ├── favicon.ico
    │       ├── media/                # Загруженные медиа
    │       │   └── ...
    │       ├── css/
    │       │   └── ...
    │       └── js/
    │           └── ...
    │
    ├── alembic/                   # Alembic миграции
    │   ├── versions/
    │   ├── env.py
    │   └── script.py.mako
    │
    └── tests/                        # Тесты
        ├── __init__.py
        ├── conftest.py               # Фикстуры pytest
        ├── integration/              # Интеграционные тесты
        │   ├── .../
        │   │   ├── ...
        │   │   └── ...
        │   └── .../
        │       ├── ...
        │       └── ...
        │
        └── unit/                     # Юнит-тесты
            ├── .../
            │   ├── ...
            │   └── ...
            └── .../
                ├── ...
                └── ...
```

## Установка и Запуск (Docker Compose)

1.  **Клонируйте репозиторий:**
    ```bash
    git clone <your-repo-url>
    cd microblog
    ```

2.  **Создайте и настройте `.env` файл:**
    Скопируйте `.env.example` в `.env`.
    ```bash
    cp .env.example .env
    ```
    Отредактируйте `.env`, установив **НАДЕЖНЫЙ** `SECRET_KEY` и, при необходимости, измените другие настройки (пароли БД и т.д.). Убедитесь, что `DATABASE_URL_ALEMBIC` использует *синхронный* формат (`postgresql://...`).

3.  **Соберите и запустите контейнеры:**
    ```bash
    docker-compose up --build -d
    ```
    *   При первом запуске Docker Compose автоматически соберет образ приложения, запустит контейнер с PostgreSQL и контейнер с приложением.
    *   Команда запуска в `docker-compose.yml` сначала применит миграции Alembic (`alembic upgrade head`), а затем запустит Uvicorn сервер.

4.  **Проверка работы:**
    *   **API:** Доступно по адресу `http://localhost:8000`
    *   **Swagger UI:** Документация API доступна по `http://localhost:8000/docs`
    *   **ReDoc:** Альтернативная документация доступна по `http://localhost:8000/redoc`
    *   **База данных:** PostgreSQL доступен на хосте по порту `5433` (для подключения внешними инструментами, например, DBeaver или pgAdmin).

## Локальная Разработка (Без Docker)

1.  **Установите Python 3.12+**.
2.  **Установите PostgreSQL** и запустите сервер.
3.  **Создайте базу данных и пользователя** в PostgreSQL согласно настройкам, которые вы укажете в `.env`.
4.  **Создайте и активируйте виртуальное окружение:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate  # Windows
    ```
5.  **Установите зависимости:**
    ```bash
    pip install -r requirements-dev.txt
    ```
6.  **Создайте `.env` файл:** Скопируйте `.env.example`, укажите ваш `SECRET_KEY` и настройки для подключения к **локальному** PostgreSQL (измените `POSTGRES_HOST` на `localhost` или `127.0.0.1`, и `DATABASE_URL_ALEMBIC` соответственно).
7.  **Примените миграции Alembic:**
    ```bash
    alembic upgrade head
    ```
8.  **Запустите приложение FastAPI:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

## Миграции Базы Данных (Alembic)

*   **Создание новой миграции (после изменений в моделях):**
    ```bash
    # Запуск внутри контейнера (рекомендуется)
    docker-compose exec app alembic revision --autogenerate -m "Краткое описание изменений"
    # Или локально (если настроено окружение)
    # alembic revision --autogenerate -m "Краткое описание изменений"
    ```
    *Проверьте сгенерированный файл миграции в `migrations/versions/`.*


*   **Применение миграций:**
    ```bash
    # Запуск внутри контейнера
    docker-compose exec app alembic upgrade head
    # Или локально
    # alembic upgrade head
    ```
    *(Docker Compose автоматически применяет миграции при старте контейнера `app`)*


*   **Откат миграции:**
    ```bash
    # Откат на одну версию назад
    docker-compose exec app alembic downgrade -1
    # Или локально
    # alembic downgrade -1
    ```

## API Ключи и Наполнение Данными (Seeding)

*   **Аутентификация:** Для доступа к защищенным эндпоинтам требуется передавать валидный API ключ пользователя в HTTP-заголовке `api-key` (имя заголовка можно изменить в `.env` через `API_KEY_HEADER`).
  
* **Создание пользователей:** Регистрация пользователей не предусмотрена. Пользователей нужно добавить вручную в базу данных.
    *   **Способ 1 (psql в Docker):**
        ```bash
        # Подключиться к контейнеру БД
        docker exec -it microblog_db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} # Замените переменные на значения из .env
        # Выполнить SQL (пример)
        INSERT INTO users (name, api_key) VALUES ('Alice', 'alice_secret_key_123');
        INSERT INTO users (name, api_key) VALUES ('Bob', 'bob_secret_key_456');
        \q
        ```
    *   **Способ 2 (Seed Script):** Запустите Python скрипт `seed.py` для добавления тестовых данных (пользователей, твитов, подписок). Запустите его после старта контейнеров (`python seed.py`).

## Тестирование

1.  **Настройте `pytest.ini`:** Убедитесь, что `TESTING=True` и `TEST_DB_URL` (например, SQLite) установлены в секции `env`.
2.  **Запустите тесты:**
    ```bash
    # Запуск внутри контейнера (если зависимости для тестов установлены в образе)
    # docker-compose exec app pytest tests/
    # Или локально (предпочтительно)
    pytest
    ```
3.  **Просмотр покрытия:** Отчет о покрытии будет выведен в консоль после запуска тестов (согласно `addopts` в `pytest.ini`).

## Остановка Приложения (Docker)

```bash
docker-compose down
```
Эта команда остановит и удалит контейнеры app и db. Данные в томах (postgres_data, media_volume) сохранятся.

Чтобы удалить и тома **(ВНИМАНИЕ: все данные БД и медиа будут удалены!)**:

```bash
docker-compose down -v
```


Убедитесь, что вы создали файл `.env` из `.env.example` и заполнили его корректными значениями, особенно `SECRET_KEY` и `DATABASE_URL_ALEMBIC`. Также добавьте `.env` в ваш `.gitignore`, чтобы случайно не закоммитить секреты.