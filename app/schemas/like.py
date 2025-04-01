"""Схемы Pydantic для модели Like (если нужны)."""

# В соответствии с ТЗ, отдельные схемы для Like не требуются для API ответов.
# Схема LikeInfo определена в tweet.py.
# Схема для успешного лайка/анлайка - TweetActionResult в tweet.py.

# Можно добавить внутренние схемы, если они понадобятся сервисам/репозиториям:
# from app.schemas.base import BaseModel
# class LikeBase(BaseModel):
#     user_id: int
#     tweet_id: int
#
# class LikeCreate(LikeBase):
#     pass
#
# class LikeOut(LikeBase):
#     # Можно добавить связи, если нужно
#     pass

# Пока оставляем пустым или удаляем файл.