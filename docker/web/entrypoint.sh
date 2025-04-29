#!/bin/bash

set -e

# Функция для проверки готовности БД
wait_for_db() {
    echo "Ожидание запуска PostgreSQL..."
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
    for _ in range(30):
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

# Ожидание БД
wait_for_db

# Установка прав на тома
# Указываем пользователя и группу, под которыми будет работать приложение
APP_USER=appuser
APP_GROUP=appgroup
echo "Установка владельца для /media и /logs на ${APP_USER}:${APP_GROUP}..."
# Используем chown для изменения владельца точки монтирования тома
# Это нужно делать от root перед понижением привилегий
chown -R "${APP_USER}:${APP_GROUP}" /media
chown -R "${APP_USER}:${APP_GROUP}" /logs
echo "Права установлены."

# Применяем миграции Alembic
echo "Применение миграций Alembic..."
#su-exec appuser alembic upgrade head
su-exec "${APP_USER}" alembic upgrade head

# Запускаем основное приложение Uvicorn
echo "Запуск основного приложения Uvicorn..."
#exec su-exec appuser uvicorn src.main:app --host 0.0.0.0 --port 8000
exec su-exec "${APP_USER}" uvicorn src.main:app --host 0.0.0.0 --port 8000
# exec su-exec appuser uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload # Для разработки
