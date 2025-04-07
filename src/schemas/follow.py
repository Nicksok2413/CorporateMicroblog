# Отдельные схемы для Follow не требуются для API ответов.

# Информация о подписчиках/подписках представлена схемой BaseUser, которая используется внутри схемы UserProfile (из src/schemas/user.py).

# Ответы для эндпоинтов подписки/отписки (POST/DELETE /users/{id}/follow) используют общую схему ResultTrue (из src/schemas/base.py).