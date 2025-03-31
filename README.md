# Сервис микроблогов

## Запуск
```bash
cp .env.example .env  # Настройте переменные
docker-compose up -d
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

- `POSTGRES_*` — настройки PostgreSQL
- `API_KEY` — ключ для авторизации (можно сгенерировать через `openssl rand -hex 16`) # ?
- `DEBUG` — режим отладки (True/False)
- `TESTING` — режим тестирования (использует SQLite)