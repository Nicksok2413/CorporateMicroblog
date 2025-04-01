"""
Модуль для функций и утилит, связанных с безопасностью.

В данном проекте основная логика аутентификации (проверка API ключа)
реализована как зависимость FastAPI в `app.api.v1.dependencies`,
так как ей требуется доступ к сессии БД и заголовкам запроса.

Этот файл может содержать:
- Функции для хеширования и проверки паролей (если потребуется).
- Функции для работы с JWT (если потребуется).
- Определения схем безопасности для OpenAPI.
- Другие утилиты безопасности.
"""

# Пример функций для работы с паролями (если бы они понадобились)
# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """
#     Проверяет соответствие простого пароля хешированному.
#
#     Args:
#         plain_password: Пароль в открытом виде.
#         hashed_password: Хешированный пароль из БД.
#
#     Returns:
#         True, если пароли совпадают, иначе False.
#     """
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password: str) -> str:
#     """
#     Генерирует хеш пароля.
#
#     Args:
#         password: Пароль в открытом виде.
#
#     Returns:
#         Хешированный пароль.
#     """
#     return pwd_context.hash(password)

# На данный момент для проекта с API ключами этот файл может быть почти пустым.
print("Модуль core.security загружен (в основном для будущих расширений).")
