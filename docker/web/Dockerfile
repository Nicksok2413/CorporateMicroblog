FROM python:3.12-slim

# Вывод логов Python сразу в stdout/stderr
ENV PYTHONUNBUFFERED=1
# Не создавать .pyc файлы
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Системные зависимости для psycopg
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем alembic.ini и папку alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./alembic /app/alembic

# Копируем код приложения
COPY ./src /app/src

# Копируем entrypoint
COPY ./docker/web/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]