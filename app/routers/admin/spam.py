from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.schemas import (
    SpamItemResponse,
    SpamResponse,
    SpamBatchRequest,
    SpamBatchResponse,
    SpamStats,
    MarkCommentAsSpamRequest,
    CommentPaginationInfo,
    PostWithSpamItems,
    PostInfo
)
from app.crud import comments as crud_comments
from datetime import datetime
import math
from collections import defaultdict

router = APIRouter()


def format_spam_response(comment) -> SpamItemResponse:
    """Format spam item (comment) for API response"""
    # Get author info from user or fallback
    if comment.user:
        author = comment.user.full_name or comment.user.username
        email = comment.user.email
        url = comment.user.website
    else:
        author = "Anonymous"
        email = "unknown@example.com"
        url = None
    
    return SpamItemResponse(
        id=comment.id,
        body=comment.body,  # Using 'body' field as defined in CommentBase schema
        author=author,
        email=email,
        url=url,
        ip=comment.user_ip or "unknown",
        status="rejected" if comment.status == "denied" else comment.status,  # Map denied to rejected
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


def group_spam_by_post(comments) -> List[PostWithSpamItems]:
    """Group spam comments by their associated posts"""
    posts_dict = defaultdict(list)
    
    # Group comments by post
    for comment in comments:
        post_id = comment.post.id
        posts_dict[post_id].append(comment)
    
    # Convert to PostWithSpamItems structure
    grouped_data = []
    for post_id, post_comments in posts_dict.items():
        # Get post info from the first comment (all comments have the same post info)
        first_comment = post_comments[0]
        post_info = PostInfo(
            id=first_comment.post.id,
            title=first_comment.post.title,
            url=first_comment.post.url
        )
        
        # Format all spam items for this post
        formatted_spam = [format_spam_response(comment) for comment in post_comments]
        
        grouped_data.append(PostWithSpamItems(
            post=post_info,
            comments=formatted_spam
        ))
    
    return grouped_data


@router.get("/spam", response_model=SpamResponse)
async def get_admin_spam(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of spam items per page"),
    status: Optional[str] = Query(None, description="Filter by status (spam, approved, rejected)"),
    search: Optional[str] = Query(None, description="Search in content and author"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get spam items for admin panel with pagination and filtering"""
    
    # Parse dates
    parsed_date_from = None
    parsed_date_to = None
    
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_from format. Use ISO format."
            )
    
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_to format. Use ISO format."
            )
    
    # If no status filter, show only spam items by default
    if status is None:
        status = "spam"
    
    spam_items, total_items, stats = await crud_comments.get_spam_items_with_pagination(
        db=db,
        page=page,
        limit=limit,
        status=status,
        search=search,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        sort=sort,
        order=order
    )
    
    # Calculate pagination info
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    # Group spam items by posts
    grouped_spam = group_spam_by_post(spam_items)
    
    pagination = CommentPaginationInfo(
        page=page,
        limit=limit,
        total=total_items,
        pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    # Get spam-specific stats
    spam_stats_data = await crud_comments.get_spam_stats(db)
    spam_stats = SpamStats(
        total=spam_stats_data["total"],
        spam=spam_stats_data["spam"],
        approved=spam_stats_data["approved"],
        rejected=spam_stats_data["rejected"]
    )
    
    return SpamResponse(
        data=grouped_spam,
        pagination=pagination,
        stats=spam_stats
    )


@router.put("/spam/{spam_id}/status")
async def update_spam_status(
    spam_id: int,
    status_update: dict,  # {"status": "spam" | "approved" | "rejected"}
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update spam item status"""
    
    new_status = status_update.get("status")
    if new_status not in ["spam", "approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'spam', 'approved', or 'rejected'"
        )
    
    comment = await crud_comments.update_spam_status(db, spam_id, new_status)
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spam item not found"
        )
    
    return format_spam_response(comment)


@router.delete("/spam/{spam_id}")
async def delete_spam_item(
    spam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a spam item"""
    
    success = await crud_comments.delete_comment(db, spam_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spam item not found"
        )
    
    return {"success": True, "message": "Spam item deleted successfully"}


@router.post("/spam/batch", response_model=SpamBatchResponse)
async def batch_update_spam(
    batch_request: SpamBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Perform batch actions on multiple spam items"""
    
    if not batch_request.spam_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No spam IDs provided"
        )
    
    try:
        if batch_request.action == "delete":
            processed = await crud_comments.bulk_delete_comments(
                db, batch_request.spam_ids
            )
        elif batch_request.action == "approve":
            processed = await crud_comments.bulk_update_spam_status(
                db, batch_request.spam_ids, "approve"
            )
        elif batch_request.action == "reject":
            processed = await crud_comments.bulk_update_spam_status(
                db, batch_request.spam_ids, "reject"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action"
            )
        
        return SpamBatchResponse(
            success=True,
            processed=processed
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch operation failed: {str(e)}"
        )


@router.post("/spam/mark-comment")
async def mark_comment_as_spam(
    request: MarkCommentAsSpamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a specific comment as spam"""
    
    comment = await crud_comments.mark_comment_as_spam(db, request.comment_id)
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return format_spam_response(comment)


@router.get("/spam/stats", response_model=SpamStats)
async def get_spam_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get spam statistics"""
    
    stats = await crud_comments.get_spam_stats(db)
    
    return SpamStats(
        total=stats["total"],
        spam=stats["spam"],
        approved=stats["approved"],
        rejected=stats["rejected"]
    )
