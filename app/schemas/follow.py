"""Схемы Pydantic для модели Follow (если нужны)."""

# В соответствии с ТЗ, отдельные схемы для Follow не требуются для API ответов.
# Схема BaseUser используется для списков followers/following в UserProfile.
# Схема для успешной подписки/отписки - ResultTrue в base.py.

# Можно добавить внутренние схемы:
# from app.schemas.base import BaseModel
# class FollowBase(BaseModel):
#     follower_id: int
#     following_id: int
#
# class FollowCreate(FollowBase):
#     pass

# Пока оставляем пустым или удаляем файл.