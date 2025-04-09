#!/bin/bash

# Выход при любой ошибке
set -e

# Функция для проверки готовности БД
wait_for_db() {
    echo "Ожидание запуска PostgreSQL..."
    # Цикл будет пытаться подключиться, пока не получится
    python << END
import os
import psycopg
import sys
import time

conn_str = (
    f"dbname={os.environ['POSTGRES_DB']} "
    f"user={os.environ['POSTGRES_USER']} "
    f"password={os.environ['POSTGRES_PASSWORD']} "
    f"host={os.environ['POSTGRES_HOST']} "
    f"port={os.environ['POSTGRES_PORT']}"
)

try:
    conn = None
    print("Попытка подключения к БД...")
    for _ in range(30): # Пытаемся в течение ~30 секунд
        try:
            conn = psycopg.connect(conn_str, connect_timeout=2)
            print("PostgreSQL запущен - соединение установлено.")
            break
        except psycopg.OperationalError as exc:
            print(f"PostgreSQL недоступен, ожидание... ({exc})")
            time.sleep(1)
    if conn is None:
        print("Не удалось подключиться к PostgreSQL после 30 секунд.")
        sys.exit(1)
    conn.close()
except KeyError as exc:
    print(f"Ошибка: переменная окружения {exc} не установлена.")
    sys.exit(1)
except Exception as exc:
    print(f"Произошла ошибка при проверке БД (psycopg3): {exc}")
    sys.exit(1)
END
}

# Дожидаемся БД
wait_for_db

# Применяем миграции Alembic
echo "Применение миграций Alembic..."
# Запускаем от имени пользователя, чтобы права на файлы были корректными, если нужно
# su-exec appuser alembic upgrade head
# Или просто:
alembic upgrade head

# Запускаем основное приложение (Uvicorn)
echo "Запуск основного приложения Uvicorn..."
# exec su-exec appuser uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload # Для разработки
exec uvicorn src.main:app --host 0.0.0.0 --port 8000