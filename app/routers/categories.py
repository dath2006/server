from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.schemas import PublicCategoryResponse
from app.crud import categories as crud_categories
from app.models import Category, Post

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[PublicCategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all categories for dropdown/selection purposes.
    Returns only publicly listed categories with post counts.
    """
    # Get categories with post counts
    query = select(
        Category,
        func.count(Post.id).label('post_count')
    ).outerjoin(Post).group_by(Category.id).filter(Category.is_listed == True).order_by(Category.display_order, Category.name)
    
    result = await db.execute(query)
    categories_with_counts = result.all()
    
    # Format the response
    formatted_categories = []
    for category, post_count in categories_with_counts:
        formatted_categories.append({
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "isListed": category.is_listed,
            "postCount": post_count or 0,
            "createdAt": category.created_at.isoformat() if category.created_at else "",
            "updatedAt": category.updated_at.isoformat() if category.updated_at else ""
        })
    
    return formatted_categories
