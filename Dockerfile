FROM python:3.12-slim

# Устанавливаем переменные окружения
# Вывод логов Python сразу в stdout/stderr
ENV PYTHONUNBUFFERED=1
# Не создавать .pyc файлы
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Системные зависимости (если нужны)
# Например, для psycopg2 могут понадобиться build-essentials и libpq-dev
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
# Для slim-образа Debian:
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY ./requirements.txt /app/requirements.txt

# Устанавливаем зависимости
# --no-cache-dir уменьшает размер образа
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения и Alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./alembic /app/alembic
COPY ./src /app/src

# Указываем порт, который будет слушать приложение
EXPOSE 8000

# Определяем точку входа
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# CMD по умолчанию (если entrypoint не задан или для передачи аргументов)
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
