from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func, desc, asc, delete, or_, update
from sqlalchemy.orm import selectinload
from app.models import Category, Post
from app.schemas import CategoryCreate, CategoryUpdate, CreateCategoryData, UpdateCategoryData
import re


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from category name"""
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


async def get_category(db: AsyncSession, category_id: int) -> Optional[Category]:
    """Get a single category by ID"""
    result = await db.execute(select(Category).filter(Category.id == category_id))
    return result.scalar_one_or_none()


async def get_category_by_slug(db: AsyncSession, slug: str) -> Optional[Category]:
    """Get a category by slug"""
    result = await db.execute(select(Category).filter(Category.slug == slug))
    return result.scalar_one_or_none()


async def get_categories_with_pagination(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    is_listed: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Category], int]:
    """Get categories with pagination, filtering, and sorting"""
    
    # Build the base query with post count
    query = select(
        Category,
        func.count(Post.id).label('post_count')
    ).outerjoin(Post).group_by(Category.id)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Category.name.ilike(search_term),
                Category.description.ilike(search_term)
            )
        )
    
    if is_listed is not None:
        query = query.where(Category.is_listed == is_listed)
    
    # Get total count for pagination
    count_query = select(func.count(Category.id))
    if search:
        search_term = f"%{search}%"
        count_query = count_query.where(
            or_(
                Category.name.ilike(search_term),
                Category.description.ilike(search_term)
            )
        )
    if is_listed is not None:
        count_query = count_query.where(Category.is_listed == is_listed)
    
    total_result = await db.execute(count_query)
    total_categories = total_result.scalar()
    
    # Apply sorting
    if sort_by == "name":
        order_column = Category.name
    elif sort_by == "created_at":
        order_column = Category.created_at
    elif sort_by == "updated_at":
        order_column = Category.updated_at
    elif sort_by == "display_order":
        order_column = Category.display_order
    elif sort_by == "post_count":
        order_column = func.count(Post.id)
    else:
        order_column = Category.name
    
    if sort_order == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(asc(order_column))
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    categories_with_count = result.all()
    
    # Add post_count to category objects
    categories = []
    for category, post_count in categories_with_count:
        category.post_count = post_count
        categories.append(category)
    
    return categories, total_categories


async def get_categories(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_listed: Optional[bool] = None
) -> List[Category]:
    """Get list of categories with optional filtering"""
    query = select(Category)
    
    if is_listed is not None:
        query = query.filter(Category.is_listed == is_listed)
    
    query = query.order_by(Category.display_order, Category.name).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def create_category(db: AsyncSession, category: CreateCategoryData, user_id: int) -> Category:
    """Create a new category"""
    # Generate slug if not provided
    slug = category.slug if category.slug else generate_slug(category.name)
    
    # Ensure slug is unique
    existing = await get_category_by_slug(db, slug)
    if existing:
        # Add a number suffix to make it unique
        counter = 1
        base_slug = slug
        while existing:
            slug = f"{base_slug}-{counter}"
            existing = await get_category_by_slug(db, slug)
            counter += 1
    
    db_category = Category(
        name=category.name,
        slug=slug,
        description=category.description,
        is_listed=category.is_listed,
        display_order=category.display_order,
        user_id=user_id
    )
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


async def update_category(db: AsyncSession, category_id: int, category_update: UpdateCategoryData) -> Optional[Category]:
    """Update an existing category"""
    category = await get_category(db, category_id)
    if not category:
        return None
    
    update_data = category_update.model_dump(exclude_unset=True)
    
    # Handle slug update
    if "name" in update_data and "slug" not in update_data:
        # Auto-generate slug from new name
        update_data["slug"] = generate_slug(update_data["name"])
    elif "slug" in update_data:
        # Ensure slug is unique
        existing = await get_category_by_slug(db, update_data["slug"])
        if existing and existing.id != category_id:
            # Add a number suffix to make it unique
            counter = 1
            base_slug = update_data["slug"]
            while existing and existing.id != category_id:
                update_data["slug"] = f"{base_slug}-{counter}"
                existing = await get_category_by_slug(db, update_data["slug"])
                counter += 1
    
    # Update the category
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int) -> bool:
    """Delete a single category"""
    category = await get_category(db, category_id)
    if not category:
        return False
    
    await db.delete(category)
    await db.commit()
    return True


async def bulk_delete_categories(db: AsyncSession, category_ids: List[int]) -> int:
    """Delete multiple categories and return count of deleted items"""
    result = await db.execute(delete(Category).where(Category.id.in_(category_ids)))
    await db.commit()
    return result.rowcount


async def toggle_category_visibility(db: AsyncSession, category_id: int) -> Optional[Category]:
    """Toggle the is_listed status of a category"""
    category = await get_category(db, category_id)
    if not category:
        return None
    
    category.is_listed = not category.is_listed
    await db.commit()
    await db.refresh(category)
    return category


async def search_categories(db: AsyncSession, search_query: str, limit: int = 50) -> List[Category]:
    """Search categories by name or description"""
    search_term = f"%{search_query}%"
    query = select(Category).where(
        or_(
            Category.name.ilike(search_term),
            Category.description.ilike(search_term)
        )
    ).order_by(Category.name).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_category_stats(db: AsyncSession) -> dict:
    """Get category statistics"""
    # Total categories
    total_result = await db.execute(select(func.count(Category.id)))
    total = total_result.scalar()
    
    # Listed categories
    listed_result = await db.execute(select(func.count(Category.id)).where(Category.is_listed == True))
    listed = listed_result.scalar()
    
    # Unlisted categories
    unlisted = total - listed
    
    # Total posts in all categories
    total_posts_result = await db.execute(
        select(func.count(Post.id)).where(Post.category_id.isnot(None))
    )
    total_posts = total_posts_result.scalar()
    
    return {
        "total": total,
        "listed": listed,
        "unlisted": unlisted,
        "total_posts": total_posts
    }


async def reorder_categories(db: AsyncSession, category_ids: List[int]) -> bool:
    """Update the display order of categories based on the provided order"""
    try:
        for index, category_id in enumerate(category_ids):
            await db.execute(
                update(Category)
                .where(Category.id == category_id)
                .values(display_order=index)
            )
        await db.commit()
        return True
    except Exception:
        await db.rollback()
        return False
