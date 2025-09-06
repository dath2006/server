from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, func
from app.models import Like, Post
from app.schemas import LikeCreate


async def toggle_like(db: AsyncSession, like_data: LikeCreate, ip_address: Optional[str] = None) -> dict:
    """
    Toggle like for a post. Returns dict with liked status and like count.
    """
    # Check if like already exists
    existing_like = None
    if like_data.user_id:
        result = await db.execute(
            select(Like)
            .where(Like.post_id == like_data.post_id)
            .where(Like.user_id == like_data.user_id)
        )
        existing_like = result.scalar_one_or_none()
    
    if existing_like:
        # Unlike - remove the like
        await db.delete(existing_like)
        await db.commit()
        liked = False
    else:
        # Like - add new like
        like = Like(
            post_id=like_data.post_id,
            user_id=like_data.user_id
        )
        db.add(like)
        await db.commit()
        liked = True
    
    # Get updated like count
    result = await db.execute(
        select(func.count(Like.id))
        .where(Like.post_id == like_data.post_id)
    )
    like_count = result.scalar()
    
    return {
        "liked": liked,
        "like_count": like_count
    }


async def check_like_status(db: AsyncSession, post_id: int, user_id: Optional[int] = None) -> dict:
    """
    Check if user has liked a post
    """
    liked = False
    
    if user_id:
        result = await db.execute(
            select(Like)
            .where(Like.post_id == post_id)
            .where(Like.user_id == user_id)
        )
        existing_like = result.scalar_one_or_none()
        liked = existing_like is not None
    
    return {"liked": liked}


async def get_like_count(db: AsyncSession, post_id: int) -> int:
    """
    Get the total number of likes for a post
    """
    result = await db.execute(
        select(func.count(Like.id))
        .where(Like.post_id == post_id)
    )
    return result.scalar()
