FROM python:3.12-slim

# Вывод логов Python сразу в stdout/stderr
ENV PYTHONUNBUFFERED=1
# Не создавать .pyc файлы
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (для psycopg и su-exec)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        build-essential \
        ca-certificates \
        wget \
    # Компилируем и устанавливаем su-exec
    && wget -O su-exec.tar.gz https://github.com/ncopa/su-exec/archive/master.tar.gz \
    && tar -xzf su-exec.tar.gz \
    && cd su-exec-master \
    && make \
    && cp su-exec /usr/local/bin/su-exec \
    && cd / \
    && rm -rf su-exec.tar.gz su-exec-master \
    # Удаляем ненужные для runtime пакеты сборки
    && apt-get purge -y --auto-remove build-essential wget \
    && rm -rf /var/lib/apt/lists/*

# Создаем группу и non-root пользователя appuser
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --no-create-home appuser

# Устанавливаем владельца рабочей директории до копирования файлов
RUN chown appuser:appgroup /app

# Копируем requirements.txt
COPY ./requirements.txt /app/requirements.txt
# Устанавливаем зависимости от имени root (для доступа к системным пакетам)
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы от имени appuser
COPY --chown=appuser:appgroup ./src /app/src
COPY --chown=appuser:appgroup ./alembic /app/alembic
COPY --chown=appuser:appgroup ./alembic.ini /app/alembic.ini
COPY --chown=appuser:appgroup ./docker/web/entrypoint.sh /app/entrypoint.sh

# Устанавливаем права на выполнение entrypoint
RUN chmod +x /app/entrypoint.sh

# Создаем директории для логов и медиа и устанавливаем владельца
# Эти директории будут перекрыты томами, но полезно иметь их с правильными правами в образе
RUN mkdir -p /logs && chown appuser:appgroup /logs
RUN mkdir -p /media && chown appuser:appgroup /media

# Открываем порт 8000
EXPOSE 8000

# Точка входа
ENTRYPOINT ["/app/entrypoint.sh"]