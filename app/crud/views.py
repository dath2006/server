from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models import View
from app.schemas import ViewCreate


async def record_view(db: AsyncSession, view_data: ViewCreate, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
    """
    Record a view for a post. Returns dict with view count.
    Only records one view per user per post (to prevent spam).
    """
    # Check if view already exists for this user/IP
    existing_view = None
    
    if view_data.user_id:
        # Check by user_id
        result = await db.execute(
            select(View)
            .where(View.post_id == view_data.post_id)
            .where(View.user_id == view_data.user_id)
        )
        existing_view = result.scalar_one_or_none()
    elif ip_address:
        # Check by IP address for anonymous users
        result = await db.execute(
            select(View)
            .where(View.post_id == view_data.post_id)
            .where(View.ip_address == ip_address)
        )
        existing_view = result.scalar_one_or_none()
    
    # Only add view if it doesn't exist
    if not existing_view:
        view = View(
            post_id=view_data.post_id,
            user_id=view_data.user_id,
            ip_address=ip_address or view_data.ip_address,
            user_agent=user_agent
        )
        db.add(view)
        await db.commit()
    
    # Get updated view count
    result = await db.execute(
        select(func.count(View.id))
        .where(View.post_id == view_data.post_id)
    )
    view_count = result.scalar()
    
    return {
        "view_count": view_count
    }


async def get_view_count(db: AsyncSession, post_id: int) -> int:
    """
    Get the total number of views for a post
    """
    result = await db.execute(
        select(func.count(View.id))
        .where(View.post_id == post_id)
    )
    return result.scalar()
