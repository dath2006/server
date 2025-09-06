from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from app.models import Tag
from app.schemas import TagCreate, TagUpdate


async def get_tag(db: AsyncSession, tag_id: int) -> Optional[Tag]:
    """Get a single tag by ID"""
    result = await db.execute(select(Tag).filter(Tag.id == tag_id))
    return result.scalar_one_or_none()


async def get_tag_by_name_and_post(db: AsyncSession, name: str, post_id: int) -> Optional[Tag]:
    """Get a tag by name for a specific post"""
    result = await db.execute(
        select(Tag).filter(and_(Tag.name == name, Tag.post_id == post_id))
    )
    return result.scalar_one_or_none()


async def get_tags(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    post_id: Optional[int] = None
) -> List[Tag]:
    """Get list of tags with optional post filter"""
    query = select(Tag)
    
    if post_id:
        query = query.filter(Tag.post_id == post_id)
    
    query = query.offset(skip).limit(limit).order_by(Tag.name)
    result = await db.execute(query)
    return result.scalars().all()


async def get_tags_for_post(db: AsyncSession, post_id: int) -> List[Tag]:
    """Get all tags for a specific post"""
    result = await db.execute(
        select(Tag)
        .filter(Tag.post_id == post_id)
        .order_by(Tag.name)
    )
    return result.scalars().all()


async def create_tag(db: AsyncSession, tag: TagCreate) -> Tag:
    """Create a new tag"""
    db_tag = Tag(**tag.model_dump())
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag


async def update_tag(
    db: AsyncSession, 
    tag_id: int, 
    tag_update: TagUpdate
) -> Optional[Tag]:
    """Update a tag"""
    result = await db.execute(select(Tag).filter(Tag.id == tag_id))
    db_tag = result.scalar_one_or_none()
    if not db_tag:
        return None

    update_data = tag_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tag, field, value)

    await db.commit()
    await db.refresh(db_tag)
    return db_tag


async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
    """Delete a tag"""
    result = await db.execute(select(Tag).filter(Tag.id == tag_id))
    db_tag = result.scalar_one_or_none()
    if not db_tag:
        return False

    await db.delete(db_tag)
    await db.commit()
    return True


async def get_or_create_tags(db: AsyncSession, tag_names: List[str], post_id: int, user_id: int) -> List[Tag]:
    """Get existing tags or create new ones for a post"""
    tags = []
    for tag_name in tag_names:
        # Try to get existing tag for this post
        existing_tag = await get_tag_by_name_and_post(db, tag_name, post_id)
        if existing_tag:
            tags.append(existing_tag)
        else:
            # Create new tag
            new_tag = TagCreate(name=tag_name, post_id=post_id, user_id=user_id)
            created_tag = await create_tag(db, new_tag)
            tags.append(created_tag)
    return tags


async def get_popular_tags(db: AsyncSession, limit: int = 10) -> List[dict]:
    """Get most popular tags (by frequency of use)"""
    result = await db.execute(
        select(Tag.id, Tag.name, func.count(Tag.id).label('count'))
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(Tag.id).desc())
        .limit(limit)
    )
    return [{"id": row.id, "name": row.name, "count": row.count} for row in result]
