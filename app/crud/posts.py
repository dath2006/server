from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models import Post, User, Comment, Upload, Tag, PostAttribute, Category, Like, Share, View
from app.schemas import PostCreate, PostUpdate


async def get_post(db: AsyncSession, post_id: int) -> Optional[Post]:
    """Get post by ID with all related data"""
    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.user),
            selectinload(Post.tags),
            selectinload(Post.comments).selectinload(Comment.user),
            selectinload(Post.uploads),
            selectinload(Post.likes).selectinload(Like.user),
            selectinload(Post.shares).selectinload(Share.user),
            selectinload(Post.views).selectinload(View.user),
            selectinload(Post.attributes),
            selectinload(Post.category)
        )
        .where(Post.id == post_id)
    )
    return result.scalar_one_or_none()


async def get_posts(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    post_type: Optional[str] = None
) -> List[Post]:
    """Get list of posts with optional filters"""
    query = select(Post).options(
        selectinload(Post.user),
        selectinload(Post.tags),
        selectinload(Post.comments).selectinload(Comment.user),
        selectinload(Post.uploads),
        selectinload(Post.attributes),
        selectinload(Post.category),
        selectinload(Post.likes).selectinload(Like.user),
        selectinload(Post.shares).selectinload(Share.user),
        selectinload(Post.views).selectinload(View.user)
    )
    
    # Join PostAttribute once, using LEFT OUTER JOIN to include posts even without attributes
    # Use INNER JOIN if we're filtering by status to ensure we only get posts with that status
    if status:
        query = query.join(PostAttribute).where(PostAttribute.status == status)
    else:
        query = query.join(PostAttribute, isouter=True)
        
    if user_id:
        query = query.where(Post.user_id == user_id)
    if post_type:
        query = query.where(Post.type == post_type)
    
    # Order by the created_at from PostAttribute since that's where timestamps are now
    query = query.offset(skip).limit(limit).order_by(PostAttribute.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_pinned_posts(db: AsyncSession) -> List[Post]:
    """Get pinned posts"""
    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.user),
            selectinload(Post.comments).selectinload(Comment.user),
            selectinload(Post.uploads),
            selectinload(Post.attributes),
            selectinload(Post.category)
        )
        .join(PostAttribute)
        .where(PostAttribute.pinned == True, PostAttribute.status == "published")
        .order_by(PostAttribute.created_at.desc())
    )
    return result.scalars().all()


async def create_post(db: AsyncSession, post: PostCreate, user_id: int) -> Post:
    """Create new post"""
    # Create the main post record with the new schema fields
    db_post = Post(
        type=post.type or "text",
        url=post.url or "",
        user_id=user_id,
        title=post.title,
        category_id=None,  # Will be handled separately if needed
        body=post.body,
        caption=post.caption,
        description=None,  # Not in new schema
        quote=post.quote,
        quote_source=post.quote_source,
        link_url=post.link_url,
        thumbnail=post.link_thumbnail or post.video_thumbnail  # Map from new fields
    )
    db.add(db_post)
    await db.flush()  # Get the ID without committing
    
    # Create post attributes record
    post_attr = PostAttribute(
        post_id=db_post.id,
        status=post.status or "published",
        pinned=post.pinned or False,
        slug=post.url or f"post-{db_post.id}",
        license="All Rights Reserved"
    )
    db.add(post_attr)
    
    # Handle tags if provided
    if post.tag_names:
        for tag_name in post.tag_names:
            tag = Tag(
                post_id=db_post.id,
                user_id=user_id,
                name=tag_name
            )
            db.add(tag)
    
    await db.commit()
    await db.refresh(db_post)
    
    # Re-fetch the post with all relationships loaded
    return await get_post(db, db_post.id)


async def update_post(db: AsyncSession, post_id: int, post_update: PostUpdate) -> Optional[Post]:
    """Update post"""
    # Get the existing post
    db_post = await get_post(db, post_id)
    if not db_post:
        return None
    
    update_data = post_update.model_dump(exclude_unset=True)
    
    # Update basic fields if provided
    if update_data:
        await db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(**update_data)
        )
    
    await db.commit()
    return await get_post(db, post_id)


async def delete_post(db: AsyncSession, post_id: int) -> bool:
    """Delete post"""
    result = await db.execute(
        delete(Post).where(Post.id == post_id)
    )
    await db.commit()
    return result.rowcount > 0
