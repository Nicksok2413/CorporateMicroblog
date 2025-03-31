from fastapi import APIRouter

from app.api.v1.routes import follow
from app.api.v1.routes import likes
from app.api.v1.routes import media
from app.api.v1.routes import tweets

router = APIRouter()

router.include_router(follow.router)
router.include_router(likes.router)
router.include_router(media.router)
router.include_router(tweets.router)
