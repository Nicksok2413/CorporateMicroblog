# Этап 1: Базовый образ с Python
FROM python:3.12-slim as python-base

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Системные зависимости (если нужны, например, для psycopg2 )
# RUN apt-get update && apt-get install --no-install-recommends -y build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Этап 2: Установка зависимостей
FROM python-base as builder

# Установка зависимостей для сборки (если нужны)
# RUN apt-get update && apt-get install --no-install-recommends -y build-essential && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .
# Опционально: копируем dev-зависимости для билда, если нужны
# COPY requirements-dev.txt .

# Устанавливаем зависимости
# --no-cache-dir уменьшает размер образа
RUN pip install --no-cache-dir -r requirements.txt

# Этап 3: Финальный образ
FROM python-base as final

# Копируем установленные зависимости из builder'а
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения
COPY ./app /app/app
COPY ./migrations /app/migrations
COPY alembic.ini /app/alembic.ini

# Создаем директорию для медиа (владелец будет root, но volume mount из docker-compose переопределит)
RUN mkdir -p /app/static/media

# Указываем порт, который будет слушать приложение
EXPOSE 8000

# Команда для запуска приложения (определена в docker-compose.yml)
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Оставляем CMD пустым или определяем его в docker-compose.yml для гибкости