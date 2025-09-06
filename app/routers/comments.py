from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.schemas import CommentCreate
from app.crud import comments as comment_crud
from app.models import Comment, User
from app.auth import get_current_active_user

router = APIRouter()

# Custom request/response models that match frontend expectations
class AuthorResponse(BaseModel):
    id: Optional[str] = None  # Convert to string for frontend
    name: str
    avatar: Optional[str] = None

class CommentCreateResponse(BaseModel):
    id: int
    author: AuthorResponse
    content: str
    created_at: datetime
    likes: int = 0

class UserComment(BaseModel):
    id: str
    author: AuthorResponse
    content: str
    body: Optional[str] = None  # For compatibility
    createdAt: str
    updatedAt: Optional[str] = None
    postId: str
    parentId: Optional[str] = None
    likes: int = 0
    replies: list = []

class UpdateCommentData(BaseModel):
    content: Optional[str] = None
    body: Optional[str] = None

class CreateCommentData(BaseModel):
    content: str
    body: Optional[str] = None
    postId: str
    parentId: Optional[str] = None


@router.post("/comment", response_model=CommentCreateResponse)
async def create_comment(
    comment_data: CommentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new comment
    """
    try:
        # Extract IP address from request
        ip_address = None
        if hasattr(request.state, 'ip_address'):
            ip_address = request.state.ip_address
        elif 'x-forwarded-for' in request.headers:
            ip_address = request.headers['x-forwarded-for'].split(',')[0].strip()
        elif 'x-real-ip' in request.headers:
            ip_address = request.headers['x-real-ip']
        else:
            ip_address = getattr(request.client, 'host', None)

        # Extract user agent from request
        user_agent = request.headers.get('user-agent')
        
        # Create the comment
        comment = await comment_crud.create_comment(
            db=db,
            comment_data=comment_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Format response to match frontend expectations
        response_data = CommentCreateResponse(
            id=comment.id,
            author=AuthorResponse(
                id=str(comment.user.id) if comment.user else None,
                name=comment.user.full_name or comment.user.username if comment.user else "Anonymous",
                avatar=comment.user.image if comment.user else None,
            ),
            content=comment.body,
            created_at=comment.created_at,
            likes=0  # Default value since likes aren't implemented yet
        )
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create comment: {str(e)}")


@router.post("/comments", response_model=UserComment)
async def create_user_comment(
    comment_data: CreateCommentData,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new comment (authenticated users)
    """
    try:
        # Extract IP address from request
        ip_address = None
        if hasattr(request.state, 'ip_address'):
            ip_address = request.state.ip_address
        elif 'x-forwarded-for' in request.headers:
            ip_address = request.headers['x-forwarded-for'].split(',')[0].strip()
        elif 'x-real-ip' in request.headers:
            ip_address = request.headers['x-real-ip']
        else:
            ip_address = getattr(request.client, 'host', None)

        # Extract user agent from request
        user_agent = request.headers.get('user-agent')
        
        # Use content or body (whichever is not empty)
        content = comment_data.content or comment_data.body or ""
        if not content:
            raise HTTPException(status_code=400, detail="Comment content cannot be empty")
        
        # Create CommentCreate object
        create_data = CommentCreate(
            post_id=int(comment_data.postId),
            content=content,
            user_id=current_user.id,
            parent_id=int(comment_data.parentId) if comment_data.parentId else None,
            ip_address=ip_address
        )
        
        # Create the comment
        comment = await comment_crud.create_comment(
            db=db,
            comment_data=create_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Format response to match frontend expectations
        response_data = UserComment(
            id=str(comment.id),
            author=AuthorResponse(
                id=str(comment.user.id) if comment.user else None,
                name=comment.user.full_name or comment.user.username if comment.user else "Anonymous",
                avatar=comment.user.image if comment.user else None,
            ),
            content=comment.body,
            body=comment.body,
            createdAt=comment.created_at.isoformat(),
            updatedAt=comment.updated_at.isoformat() if comment.updated_at else None,
            postId=str(comment.post_id),
            parentId=str(comment.parent_id) if comment.parent_id else None,
            likes=0,  # Default value since likes aren't implemented yet
            replies=[]
        )
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create comment: {str(e)}")


@router.patch("/comments/{comment_id}", response_model=UserComment)
async def update_user_comment(
    comment_id: int,
    comment_data: UpdateCommentData,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user's own comment
    """
    try:
        # Get the comment first to check ownership
        comment = await comment_crud.get_comment(db, comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user owns the comment
        if comment.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this comment")
        
        # Use content or body (whichever is not empty)
        new_content = comment_data.content or comment_data.body
        if not new_content:
            raise HTTPException(status_code=400, detail="Comment content cannot be empty")
        
        # Update the comment
        updated_comment = await comment_crud.update_comment_content(
            db=db,
            comment_id=comment_id,
            content=new_content
        )
        
        if not updated_comment:
            raise HTTPException(status_code=500, detail="Failed to update comment")
        
        # Format response to match frontend expectations
        response_data = UserComment(
            id=str(updated_comment.id),
            author=AuthorResponse(
                id=str(updated_comment.user.id) if updated_comment.user else None,
                name=updated_comment.user.full_name or updated_comment.user.username if updated_comment.user else "Anonymous",
                avatar=updated_comment.user.image if updated_comment.user else None,
            ),
            content=updated_comment.body,
            body=updated_comment.body,
            createdAt=updated_comment.created_at.isoformat(),
            updatedAt=updated_comment.updated_at.isoformat() if updated_comment.updated_at else None,
            postId=str(updated_comment.post_id),
            parentId=str(updated_comment.parent_id) if updated_comment.parent_id else None,
            likes=0,  # Default value since likes aren't implemented yet
            replies=[]
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update comment: {str(e)}")


@router.delete("/comments/{comment_id}")
async def delete_user_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete user's own comment
    """
    try:
        # Get the comment first to check ownership
        comment = await comment_crud.get_comment(db, comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user owns the comment
        if comment.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
        
        # Delete the comment
        success = await comment_crud.delete_comment(db=db, comment_id=comment_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete comment")
        
        return {
            "success": True,
            "message": "Comment deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")
