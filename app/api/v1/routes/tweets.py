from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.like_repository import LikeRepository
from app.schemas.response_schema import ResultResponse
from app.utils.auth import get_current_user


router = APIRouter()


@router.delete("/tweets/{tweet_id}/likes", response_model=ResultResponse)
async def unlike_tweet(
    tweet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Удаление лайка с твита
    """
    deleted = await LikeRepository.delete_like(db, current_user.id, tweet_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )

    return ResultResponse(result=True)
