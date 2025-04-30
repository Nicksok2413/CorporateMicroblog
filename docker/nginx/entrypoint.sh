#!/bin/sh

set -e # Выход при ошибке

# Пути к файлам сертификата и ключа внутри контейнера
CERT_FILE="/etc/nginx/certs/nginx-selfsigned.crt"
KEY_FILE="/etc/nginx/certs/nginx-selfsigned.key"
CERT_DIR="/etc/nginx/certs"

# Проверяем, существуют ли оба файла
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "Генерируем самоподписанный сертификат для разработки..."
  # Убедимся, что директория существует
  mkdir -p "$CERT_DIR"
  # Генерируем сертификат и ключ
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=XX/ST=State/L=City/O=Dev/OU=DevOps/CN=localhost" # Используем общие данные
  echo "Сертификат сгенерирован."
else
  echo "Сертификат уже существует."
fi

# Запускаем Nginx
echo "Запускаем Nginx..."
exec "$@"