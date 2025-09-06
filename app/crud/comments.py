from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func, desc, asc, delete, or_, update
from sqlalchemy.orm import selectinload, joinedload
from app.models import Comment, Post, User
from app.schemas import CommentCreate
from datetime import datetime
import math


async def create_comment(db: AsyncSession, comment_data: CommentCreate, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Comment:
    """Create a new comment"""
    comment = Comment(
        post_id=comment_data.post_id,
        user_id=comment_data.user_id,
        parent_id=comment_data.parent_id,
        body=comment_data.content,  # Use content field
        user_ip=ip_address or comment_data.ip_address,  # Use provided IP or extracted IP
        user_agent=user_agent,
        status="pending"  # Default to pending for moderation
    )
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    # Load the related user and post data
    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user), joinedload(Comment.post))
        .filter(Comment.id == comment.id)
    )
    return result.scalar_one()


async def get_comment(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    """Get a single comment by ID with related data"""
    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user), joinedload(Comment.post))
        .filter(Comment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def get_comments_with_pagination(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    author: Optional[str] = None,
    post_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = "created_at",
    order: str = "desc"
) -> Tuple[List[Comment], int, dict]:
    """Get comments with pagination, filtering, and sorting"""
    
    # Build the base query with joins
    query = select(Comment).options(
        joinedload(Comment.user),
        joinedload(Comment.post)
    )
    
    # Build count query
    count_query = select(func.count(Comment.id))
    
    # Apply filters
    filters = []
    
    if status:
        filters.append(Comment.status == status)
    
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                Comment.body.ilike(search_term),
                User.username.ilike(search_term),
                User.full_name.ilike(search_term)
            )
        )
        # Need to join User for search
        query = query.join(User, Comment.user_id == User.id, isouter=True)
        count_query = count_query.select_from(Comment).join(User, Comment.user_id == User.id, isouter=True)
    
    if author:
        author_term = f"%{author}%"
        filters.append(
            or_(
                User.username.ilike(author_term),
                User.full_name.ilike(author_term)
            )
        )
        if not search:  # Only join if not already joined
            query = query.join(User, Comment.user_id == User.id, isouter=True)
            count_query = count_query.select_from(Comment).join(User, Comment.user_id == User.id, isouter=True)
    
    if post_id:
        filters.append(Comment.post_id == post_id)
    
    if date_from:
        filters.append(Comment.created_at >= date_from)
    
    if date_to:
        filters.append(Comment.created_at <= date_to)
    
    # Apply filters to both queries
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total_comments = total_result.scalar()
    
    # Apply sorting
    if sort == "created_at":
        order_column = Comment.created_at
    elif sort == "updated_at":
        order_column = Comment.updated_at
    else:
        order_column = Comment.created_at
    
    if order == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(asc(order_column))
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    # Get stats
    stats = await get_comment_stats(db)
    
    return comments, total_comments, stats


async def get_comment_stats(db: AsyncSession) -> dict:
    """Get comment statistics"""
    # Total comments
    total_result = await db.execute(select(func.count(Comment.id)))
    total = total_result.scalar()
    
    # Comments by status
    status_result = await db.execute(
        select(Comment.status, func.count(Comment.id))
        .group_by(Comment.status)
    )
    status_counts = dict(status_result.all())
    
    return {
        "total": total,
        "pending": status_counts.get("pending", 0),
        "approved": status_counts.get("approved", 0),
        "spam": status_counts.get("spam", 0),
        "denied": status_counts.get("denied", 0)
    }


async def update_comment_status(db: AsyncSession, comment_id: int, new_status: str) -> Optional[Comment]:
    """Update comment status"""
    comment = await get_comment(db, comment_id)
    if not comment:
        return None
    
    comment.status = new_status
    await db.commit()
    await db.refresh(comment)
    return comment


async def update_comment_content(db: AsyncSession, comment_id: int, new_content: str) -> Optional[Comment]:
    """Update comment content"""
    comment = await get_comment(db, comment_id)
    if not comment:
        return None

    comment.body = new_content
    await db.commit()
    await db.refresh(comment)
    return comment


async def delete_comment(db: AsyncSession, comment_id: int) -> bool:
    """Delete a single comment"""
    comment = await get_comment(db, comment_id)
    if not comment:
        return False

    await db.delete(comment)
    await db.commit()
    return True


async def update_comment_content(db: AsyncSession, comment_id: int, content: str) -> Optional[Comment]:
    """Update comment content"""
    comment = await get_comment(db, comment_id)
    if not comment:
        return None
    
    comment.body = content
    await db.commit()
    await db.refresh(comment)
    
    # Load the related user and post data
    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user), joinedload(Comment.post))
        .filter(Comment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def bulk_update_comment_status(db: AsyncSession, comment_ids: List[int], new_status: str) -> int:
    """Bulk update comment status"""
    result = await db.execute(
        update(Comment)
        .where(Comment.id.in_(comment_ids))
        .values(status=new_status)
    )
    await db.commit()
    return result.rowcount


async def bulk_delete_comments(db: AsyncSession, comment_ids: List[int]) -> int:
    """Bulk delete comments"""
    result = await db.execute(delete(Comment).where(Comment.id.in_(comment_ids)))
    await db.commit()
    return result.rowcount


async def mark_comment_as_spam(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    """Mark a specific comment as spam"""
    return await update_comment_status(db, comment_id, "spam")


# Spam-specific functions (just filtered comments)
async def get_spam_items_with_pagination(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,  # For spam: 'spam', 'approved', 'rejected' (maps to 'denied')
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = "created_at",
    order: str = "desc"
) -> Tuple[List[Comment], int, dict]:
    """Get spam items (comments with status='spam' or related) with pagination"""
    
    # Map spam statuses to comment statuses
    if status == "rejected":
        mapped_status = "denied"
    elif status == "spam":
        mapped_status = "spam"
    elif status == "approved":
        mapped_status = "approved"
    else:
        mapped_status = None
    
    # If no specific status, default to showing spam items
    if mapped_status is None:
        # Show spam, denied, and approved (items that were once spam)
        return await get_comments_with_pagination(
            db=db, page=page, limit=limit, search=search,
            date_from=date_from, date_to=date_to, sort=sort, order=order
        )
    else:
        return await get_comments_with_pagination(
            db=db, page=page, limit=limit, status=mapped_status, search=search,
            date_from=date_from, date_to=date_to, sort=sort, order=order
        )


async def get_spam_stats(db: AsyncSession) -> dict:
    """Get spam statistics"""
    # Total spam-related items
    spam_result = await db.execute(
        select(func.count(Comment.id))
        .where(Comment.status.in_(["spam", "denied", "approved"]))
    )
    total = spam_result.scalar()
    
    # Breakdown by status
    status_result = await db.execute(
        select(Comment.status, func.count(Comment.id))
        .where(Comment.status.in_(["spam", "denied", "approved"]))
        .group_by(Comment.status)
    )
    status_counts = dict(status_result.all())
    
    return {
        "total": total,
        "spam": status_counts.get("spam", 0),
        "approved": status_counts.get("approved", 0),
        "rejected": status_counts.get("denied", 0)  # Map denied to rejected for API
    }


async def update_spam_status(db: AsyncSession, comment_id: int, new_status: str) -> Optional[Comment]:
    """Update spam item status (maps to comment status)"""
    # Map spam statuses to comment statuses
    if new_status == "rejected":
        mapped_status = "denied"
    elif new_status == "approved":
        mapped_status = "approved"
    elif new_status == "spam":
        mapped_status = "spam"
    else:
        return None
    
    return await update_comment_status(db, comment_id, mapped_status)


async def bulk_update_spam_status(db: AsyncSession, comment_ids: List[int], action: str) -> int:
    """Bulk update spam status"""
    if action == "approve":
        mapped_status = "approved"
    elif action == "reject":
        mapped_status = "denied"
    else:
        return 0
    
    return await bulk_update_comment_status(db, comment_ids, mapped_status)


async def get_comments_grouped_by_posts(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    author: Optional[str] = None,
    post_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = "created_at",
    order: str = "desc"
) -> Tuple[dict, int, dict]:
    """Get comments grouped by posts with pagination"""
    
    # First get the regular comments with pagination
    comments, total_comments, stats = await get_comments_with_pagination(
        db=db, page=page, limit=limit, status=status, search=search,
        author=author, post_id=post_id, date_from=date_from, date_to=date_to,
        sort=sort, order=order
    )
    
    # Group comments by post
    posts_dict = {}
    for comment in comments:
        post_id = comment.post_id
        if post_id not in posts_dict:
            posts_dict[post_id] = {
                'post': comment.post,
                'comments': [],
                'comment_count': 0
            }
        posts_dict[post_id]['comments'].append(comment)
        posts_dict[post_id]['comment_count'] += 1
    
    # Convert to list of PostWithComments
    grouped_data = []
    for post_data in posts_dict.values():
        grouped_data.append({
            'post': {
                'id': post_data['post'].id,
                'title': post_data['post'].title,
                'url': post_data['post'].url
            },
            'comments': post_data['comments'],
            'comment_count': post_data['comment_count']
        })
    
    return grouped_data, total_comments, stats
