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

wait_for_db

echo "Применение миграций Alembic..."
alembic upgrade head

# --- Инициализация медиа тома при первом запуске ---
MEDIA_DIR="/media"
INITIAL_MEDIA_DIR="/app/initial_media"
MARKER_FILE="$MEDIA_DIR/.volume_initialized"

# Проверяем, существует ли сама директория /media
if [ ! -d "$MEDIA_DIR" ]; then
  echo "Критическая ошибка: директория тома $MEDIA_DIR не смонтирована!"
  exit 1
fi

# Копируем, если нужно
if [ -d "$INITIAL_MEDIA_DIR" ] && [ ! -f "$MARKER_FILE" ]; then
  echo "Инициализация тома медиа: копирование начальных файлов из $INITIAL_MEDIA_DIR в $MEDIA_DIR..."
  # Копируем содержимое
  cp -a $INITIAL_MEDIA_DIR/. $MEDIA_DIR/ && \
  # Устанавливаем владельца для скопированных файлов/папок внутри /media на appuser (UID 1001)
  find $MEDIA_DIR -mindepth 1 -exec chown 1001:1001 {} + && \
  # Создаем маркерный файл
  touch $MARKER_FILE && \
  chown 1001:1001 $MARKER_FILE # Устанавливаем владельца и для маркера
  echo "Том медиа инициализирован."
else
  if [ -f "$MARKER_FILE" ]; then
     echo "Том медиа уже инициализирован."
   else
     echo "Нет начальных медиафайлов для копирования ($INITIAL_MEDIA_DIR)."
   fi
fi
# -------------------------------------------------

echo "Запуск основного приложения Uvicorn..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
# exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload # Для разработки
