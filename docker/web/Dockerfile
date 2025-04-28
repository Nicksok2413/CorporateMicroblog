FROM python:3.12-slim

# Вывод логов Python сразу в stdout/stderr
ENV PYTHONUNBUFFERED=1
# Не создавать .pyc файлы
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем рабочую директорию
WORKDIR /app

# # Установка системных зависимостей (для psycopg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Создаем группу и non-root пользователя appuser
RUN addgroup --system appgroup --gid 1001 && \
    adduser --system --ingroup appgroup --uid 1001 --no-create-home appuser

# Копируем requirements.txt
COPY ./requirements.txt /app/requirements.txt
# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы от имени appuser
COPY ./src /app/src
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./docker/web/entrypoint.sh /app/entrypoint.sh
# Копируем начальные медиа
COPY ./sample_media /app/initial_media

# Устанавливаем права на выполнение entrypoint
RUN chmod +x /app/entrypoint.sh

# Создаем директории для логов и медиа и устанавливаем владельца
# Эти директории будут перекрыты томами, но полезно иметь их с правильными правами в образе
RUN mkdir -p /logs && chown 1001:1001 /logs
RUN mkdir -p /media && chown 1001:1001 /media

# Открываем порт 8000
EXPOSE 8000

# Точка входа
ENTRYPOINT ["/app/entrypoint.sh"]