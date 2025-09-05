from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_admin_user
from app.models import User
from app.schemas import (
    CommentResponse,
    CommentsResponse,
    CommentUpdateStatus,
    CommentBatchRequest,
    CommentBatchResponse,
    CommentPaginationInfo,
    CommentStats,
    PostWithComments,
    PostInfo,
    CommentInPost,
    GroupedCommentsResponse
)
from app.crud import comments as crud_comments
from datetime import datetime
import math
from collections import defaultdict

router = APIRouter()


def format_comment_in_post(comment) -> CommentInPost:
    """Format comment for PostWithComments structure"""
    # Get author info from user or fallback
    if comment.user:
        author = comment.user.full_name or comment.user.username
        email = comment.user.email
        url = comment.user.website
    else:
        author = "Anonymous"
        email = "unknown@example.com"
        url = None
    
    return CommentInPost(
        id=comment.id,
        body=comment.body,
        author=author,
        email=email,
        url=url,
        ip=comment.user_ip or "unknown",
        status=comment.status,
        createdAt=comment.created_at,  # Use alias name
        updatedAt=comment.updated_at   # Use alias name
    )


def format_comment_response(comment) -> CommentResponse:
    """Format comment for API response"""
    # Get author info from user or fallback
    if comment.user:
        author = comment.user.full_name or comment.user.username
        email = comment.user.email
        url = comment.user.website
    else:
        author = "Anonymous"
        email = "unknown@example.com"
        url = None
    
    return CommentResponse(
        id=comment.id,
        body=comment.body,
        author=author,
        email=email,
        url=url,
        ip=comment.user_ip or "unknown",
        status=comment.status,
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


def group_comments_by_post(comments) -> List[PostWithComments]:
    """Group comments by their associated posts"""
    posts_dict = defaultdict(list)
    
    # Group comments by post
    for comment in comments:
        post_id = comment.post.id
        posts_dict[post_id].append(comment)
    
    # Convert to PostWithComments structure
    grouped_data = []
    for post_id, post_comments in posts_dict.items():
        # Get post info from the first comment (all comments have the same post info)
        first_comment = post_comments[0]
        post_info = PostInfo(
            id=first_comment.post.id,
            title=first_comment.post.title,
            url=first_comment.post.url
        )
        
        # Format all comments for this post using CommentInPost
        formatted_comments = [format_comment_in_post(comment) for comment in post_comments]
        
        grouped_data.append(PostWithComments(
            post=post_info,
            comments=formatted_comments,
            commentCount=len(formatted_comments)  # Use alias name
        ))
    
    return grouped_data


@router.get("/comments", response_model=GroupedCommentsResponse)
async def get_admin_comments(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of comments per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in comment body and author"),
    author: Optional[str] = Query(None, description="Filter by author"),
    post_id: Optional[int] = Query(None, description="Filter by post ID"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get comments for admin panel with pagination and filtering - grouped by posts"""
    
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
    
    comments, total_comments, stats = await crud_comments.get_comments_with_pagination(
        db=db,
        page=page,
        limit=limit,
        status=status,
        search=search,
        author=author,
        post_id=post_id,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        sort=sort,
        order=order
    )
    
    # Calculate pagination info
    total_pages = math.ceil(total_comments / limit) if total_comments > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    # Group comments by posts
    grouped_comments = group_comments_by_post(comments)
    
    pagination = CommentPaginationInfo(
        page=page,
        limit=limit,
        total=total_comments,
        pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    comment_stats = CommentStats(
        total=stats["total"],
        pending=stats["pending"],
        approved=stats["approved"],
        spam=stats["spam"],
        denied=stats["denied"]
    )
    
    return GroupedCommentsResponse(
        data=grouped_comments,
        pagination=pagination,
        stats=comment_stats
    )


@router.put("/comments/{comment_id}/status")
async def update_comment_status(
    comment_id: int,
    status_update: CommentUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update comment status"""
    
    comment = await crud_comments.update_comment_status(
        db, comment_id, status_update.status
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return format_comment_response(comment)


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a comment"""
    
    success = await crud_comments.delete_comment(db, comment_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return {"success": True, "message": "Comment deleted successfully"}


@router.post("/comments/batch", response_model=CommentBatchResponse)
async def batch_update_comments(
    batch_request: CommentBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Perform batch actions on multiple comments"""
    
    if not batch_request.comment_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No comment IDs provided"
        )
    
    try:
        if batch_request.action == "delete":
            processed = await crud_comments.bulk_delete_comments(
                db, batch_request.comment_ids
            )
        elif batch_request.action == "approve":
            processed = await crud_comments.bulk_update_comment_status(
                db, batch_request.comment_ids, "approved"
            )
        elif batch_request.action == "deny":
            processed = await crud_comments.bulk_update_comment_status(
                db, batch_request.comment_ids, "denied"
            )
        elif batch_request.action == "spam":
            processed = await crud_comments.bulk_update_comment_status(
                db, batch_request.comment_ids, "spam"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action"
            )
        
        return CommentBatchResponse(
            success=True,
            processed=processed
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch operation failed: {str(e)}"
        )
