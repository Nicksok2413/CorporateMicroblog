FROM nginx:1.27-alpine

# Удаляем стандартный конфиг
RUN rm /etc/nginx/conf.d/default.conf

# Копируем наш кастомный конфиг
COPY ./docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Создаем директорию для медиафайлов внутри контейнера и даем права пользователю nginx
RUN mkdir -p /var/www/media && chown nginx:nginx /var/www/media

# Создаем директории для логов и даем права
RUN mkdir -p /var/log/nginx && \
    touch /var/log/nginx/access.log /var/log/nginx/error.log && \
    chown -R nginx:nginx /var/log/nginx

# Открываем порт 80
EXPOSE 80
