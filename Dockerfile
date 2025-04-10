FROM python:3.12-slim

# Вывод логов Python сразу в stdout/stderr
ENV PYTHONUNBUFFERED=1
# Не создавать .pyc файлы
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Системные зависимости для psycopg
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./alembic.ini /app/alembic.ini
COPY ./alembic /app/alembic
COPY ./src /app/src

EXPOSE 8000

COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]