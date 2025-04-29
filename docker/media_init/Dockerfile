# Используем минимальный образ, содержащий утилиты shell (включая cp)
FROM alpine:latest

# Создаем директорию внутри образа, куда скопируем медиа с хоста
WORKDIR /init_media

# Копируем содержимое папки sample_media хоста в /init_media образа
COPY ./docker/media_init/sample_media/ /init_media/

# Создаем точку монтирования для тома данных
RUN mkdir -p /target_media_volume
