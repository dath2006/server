from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Post, PostAttribute, Comment, Like, Share, View
from app.schemas import PostResponse, PostCreate, PostUpdate, LikeCreate, ViewCreate
from app.crud import posts as post_crud, likes as like_crud, views as view_crud

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/", response_model=List[PostResponse])
async def read_posts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, description="Filter by post status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get list of posts"""
    posts = await post_crud.get_posts(
        db, skip=skip, limit=limit, status=status, user_id=user_id
    )
    return posts


@router.get("/feed", response_model=Dict[str, Any])
async def get_feed(
    limit: int = Query(10, ge=1, le=50, description="Number of posts to return"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination (post ID)"),
    search: Optional[str] = Query(None, description="Search term to filter posts"),
    db: AsyncSession = Depends(get_db)
):
    """Get compressed posts feed optimized for frontend with cursor-based pagination and search"""
    
    # For cursor-based pagination, we'll use the post ID as cursor
    # If cursor is provided, we fetch posts with ID less than cursor (older posts)
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
    
    # Join with PostAttribute for status filtering and ordering
    query = query.join(PostAttribute).where(PostAttribute.status == "published")
    
    # Apply search filter if search term is provided
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Post.title.ilike(search_term),
                Post.body.ilike(search_term),
                Post.caption.ilike(search_term),
                Post.description.ilike(search_term),
                Post.quote.ilike(search_term)
            )
        )
    
    # Apply cursor-based filtering if cursor is provided
    if cursor:
        try:
            cursor_id = int(cursor)
            query = query.where(Post.id < cursor_id)
        except (ValueError, TypeError):
            # If cursor is invalid, ignore it and return from the beginning
            pass
    
    # Order by ID descending (newest first) and apply limit
    query = query.order_by(Post.id.desc()).limit(limit)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    feed_data = []
    for post in posts:
        # Build content based on post type
        content = {}
        
        if post.type == "text":
            content["body"] = post.body
        elif post.type == "photo":
            # Get image URLs from uploads
            images = [upload.url for upload in post.uploads if upload.type == "image"]
            content["images"] = images
            content["caption"] = post.caption
        elif post.type == "video":
            # Get video URL from uploads or post fields
            video_upload = next((upload for upload in post.uploads if upload.type == "video"), None)
            content["videoUrl"] = video_upload.url if video_upload else None
            content["videoThumbnail"] = post.thumbnail
            content["caption"] = post.caption
        elif post.type == "audio":
            # Get audio URL from uploads
            audio_upload = next((upload for upload in post.uploads if upload.type == "audio"), None)
            content["audioUrl"] = audio_upload.url if audio_upload else None
            content["duration"] = "15:30"  # You might want to store this in post or upload
            content["audioDescription"] = post.caption or post.body
        elif post.type == "quote":
            content["quote"] = post.quote
            content["source"] = post.quote_source
        elif post.type == "link":
            content["url"] = post.link_url
            content["linkTitle"] = post.title
            content["linkDescription"] = post.body or post.caption
            content["linkThumbnail"] = post.thumbnail
        elif post.type == "file":
            # Get all uploads as files
            files = [
                {
                    "name": upload.name,
                    "url": upload.url,
                    "size": upload.size,
                    "type": upload.mime_type
                }
                for upload in post.uploads
            ]
            content["files"] = files
        
        # Build compressed post data
        post_data = {
            "id": str(post.id),
            "title": post.title,
            "type": post.type,
            "author": {
                "id": str(post.user.id),
                "username": post.user.username,
                "fullName": post.user.full_name,
                "image": post.user.image,
                "website": post.user.website
            } if post.user else None,
            "createdAt": post.attributes.created_at.isoformat() if post.attributes and post.attributes.created_at else None,
            "updatedAt": post.attributes.updated_at.isoformat() if post.attributes and post.attributes.updated_at else None,
            "status": post.attributes.status if post.attributes else "published",
            "pinned": post.attributes.pinned if post.attributes else False,
            "originalWork": post.attributes.original_work if post.attributes else None,
            "rightsHolder": post.attributes.rights_holder if post.attributes else None,
            "license": post.attributes.license if post.attributes else "All Rights Reserved",
            "tags": [tag.name for tag in post.tags] if post.tags else [],
            "category": post.category.name if post.category else None,
            "likes": len(post.likes) if post.likes else 0,
            "shares": len(post.shares) if post.shares else 0,
            "saves": 0,  # Implement saves functionality later
            "viewCount": len(post.views) if post.views else 0,
            "content": content,
            "comments": [
                {
                    "id": str(comment.id),
                    "body": comment.body,
                    "createdAt": comment.created_at.isoformat() if comment.created_at else None,
                    "author": {
                        "id": str(comment.user.id),
                        "username": comment.user.username,
                        "fullName": comment.user.full_name,
                        "image": comment.user.image
                    } if comment.user else None
                }
                for comment in post.comments
            ] if post.comments else []
        }
        
        feed_data.append(post_data)
    
    # Determine next cursor and hasMore
    next_cursor = None
    has_more = len(posts) == limit
    if posts and has_more:
        next_cursor = str(posts[-1].id)
    
    return {
        "data": feed_data,
        "pagination": {
            "nextCursor": next_cursor,
            "hasMore": has_more,
            "limit": limit
        }
    }
    


@router.get("/pinned", response_model=List[Dict[str, Any]])
async def read_pinned_posts(db: AsyncSession = Depends(get_db)):
    """Get pinned posts in compressed format"""
    
    # Use the same query structure as the feed endpoint for consistency
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
    
    # Join with PostAttribute to filter pinned posts
    query = query.join(PostAttribute).where(
        PostAttribute.pinned == True, 
        PostAttribute.status == "published"
    ).order_by(PostAttribute.created_at.desc())
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    pinned_data = []
    for post in posts:
        # Build content based on post type (same logic as feed)
        content = {}
        
        if post.type == "text":
            content["body"] = post.body
        elif post.type == "photo":
            # Get image URLs from uploads
            images = [upload.url for upload in post.uploads if upload.type == "image"]
            content["images"] = images
            content["caption"] = post.caption
        elif post.type == "video":
            # Get video URL from uploads or post fields
            video_upload = next((upload for upload in post.uploads if upload.type == "video"), None)
            content["videoUrl"] = video_upload.url if video_upload else None
            content["videoThumbnail"] = post.thumbnail
            content["caption"] = post.caption
        elif post.type == "audio":
            # Get audio URL from uploads
            audio_upload = next((upload for upload in post.uploads if upload.type == "audio"), None)
            content["audioUrl"] = audio_upload.url if audio_upload else None
            content["duration"] = "15:30"  # You might want to store this in post or upload
            content["audioDescription"] = post.caption or post.body
        elif post.type == "quote":
            content["quote"] = post.quote
            content["source"] = post.quote_source
        elif post.type == "link":
            content["url"] = post.link_url
            content["linkTitle"] = post.title
            content["linkDescription"] = post.body or post.caption
            content["linkThumbnail"] = post.thumbnail
        elif post.type == "file":
            # Get all uploads as files
            files = [
                {
                    "name": upload.name,
                    "url": upload.url,
                    "size": upload.size,
                    "type": upload.mime_type
                }
                for upload in post.uploads
            ]
            content["files"] = files
        
        # Build compressed post data (same format as feed)
        post_data = {
            "id": str(post.id),
            "title": post.title,
            "type": post.type,
            "author": {
                "id": str(post.user.id),
                "username": post.user.username,
                "fullName": post.user.full_name,
                "image": post.user.image,
                "website": post.user.website
            } if post.user else None,
            "createdAt": post.attributes.created_at.isoformat() if post.attributes and post.attributes.created_at else None,
            "updatedAt": post.attributes.updated_at.isoformat() if post.attributes and post.attributes.updated_at else None,
            "status": post.attributes.status if post.attributes else "published",
            "pinned": post.attributes.pinned if post.attributes else False,
            "originalWork": post.attributes.original_work if post.attributes else None,
            "rightsHolder": post.attributes.rights_holder if post.attributes else None,
            "license": post.attributes.license if post.attributes else "All Rights Reserved",
            "tags": [tag.name for tag in post.tags] if post.tags else [],
            "category": post.category.name if post.category else None,
            "likes": len(post.likes) if post.likes else 0,
            "shares": len(post.shares) if post.shares else 0,
            "saves": 0,  # Implement saves functionality later
            "viewCount": len(post.views) if post.views else 0,
            "content": content,
            "comments": [
                {
                    "id": str(comment.id),
                    "body": comment.body,
                    "createdAt": comment.created_at.isoformat() if comment.created_at else None,
                    "author": {
                        "id": str(comment.user.id),
                        "username": comment.user.username,
                        "fullName": comment.user.full_name,
                        "image": comment.user.image
                    } if comment.user else None
                }
                for comment in post.comments
            ] if post.comments else []
        }
        
        pinned_data.append(post_data)
    
    return pinned_data


@router.get("/{post_id}", response_model=Dict[str, Any])
async def read_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get individual post by ID with compressed format"""
    
    # Use the same query structure as the feed endpoint for consistency
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
    ).where(Post.id == post_id)
    
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Build content based on post type (same logic as feed)
    content = {}
    
    if post.type == "text":
        content["body"] = post.body
    elif post.type == "photo":
        # Get image URLs from uploads
        images = [upload.url for upload in post.uploads if upload.type == "image"]
        content["images"] = images
        content["caption"] = post.caption
    elif post.type == "video":
        # Get video URL from uploads or post fields
        video_upload = next((upload for upload in post.uploads if upload.type == "video"), None)
        content["videoUrl"] = video_upload.url if video_upload else None
        content["videoThumbnail"] = post.thumbnail
        content["caption"] = post.caption
    elif post.type == "audio":
        # Get audio URL from uploads
        audio_upload = next((upload for upload in post.uploads if upload.type == "audio"), None)
        content["audioUrl"] = audio_upload.url if audio_upload else None
        content["duration"] = "15:30"  # You might want to store this in post or upload
        content["audioDescription"] = post.caption or post.body
    elif post.type == "quote":
        content["quote"] = post.quote
        content["source"] = post.quote_source
    elif post.type == "link":
        content["url"] = post.link_url
        content["linkTitle"] = post.title
        content["linkDescription"] = post.body or post.caption
        content["linkThumbnail"] = post.thumbnail
    elif post.type == "file":
        # Get all uploads as files
        files = [
            {
                "name": upload.name,
                "url": upload.url,
                "size": upload.size,
                "type": upload.mime_type
            }
            for upload in post.uploads
        ]
        content["files"] = files
    
    # Build compressed post data (same format as feed)
    post_data = {
        "id": str(post.id),
        "title": post.title,
        "type": post.type,
        "url": post.url,
        "author": {
            "id": str(post.user.id),
            "username": post.user.username,
            "name": post.user.full_name,
            "image": post.user.image,
            "website": post.user.website
        } if post.user else None,
        "createdAt": post.attributes.created_at.isoformat() if post.attributes and post.attributes.created_at else None,
        "updatedAt": post.attributes.updated_at.isoformat() if post.attributes and post.attributes.updated_at else None,
        "status": post.attributes.status if post.attributes else "published",
        "pinned": post.attributes.pinned if post.attributes else False,
        "originalWork": post.attributes.original_work if post.attributes else None,
        "rightsHolder": post.attributes.rights_holder if post.attributes else None,
        "license": post.attributes.license if post.attributes else "All Rights Reserved",
        "slug": post.attributes.slug if post.attributes else None,
        "tags": [tag.name for tag in post.tags] if post.tags else [],
        "category": post.category.name if post.category else None,
        "likes": len(post.likes) if post.likes else 0,
        "shares": len(post.shares) if post.shares else 0,
        "saves": 0,  # Implement saves functionality later
        "viewCount": len(post.views) if post.views else 0,
        "content": content,
        "comments": [
            {
                "id": str(comment.id),
                "body": comment.body,
                "status": comment.status,
                "createdAt": comment.created_at.isoformat() if comment.created_at else None,
                "updatedAt": comment.updated_at.isoformat() if comment.updated_at else None,
                "author": {
                    "id": str(comment.user.id),
                    "username": comment.user.username,
                    "name": comment.user.full_name,
                    "image": comment.user.image
                } if comment.user else None,
                # Include parent comment ID for threaded comments
                "parentId": str(comment.parent_id) if comment.parent_id else None
            }
            for comment in post.comments
        ] if post.comments else [],
        # Include more detailed engagement data for individual posts
        "engagement": {
            "likesDetails": [
                {
                    "id": str(like.id),
                    "createdAt": like.created_at.isoformat() if like.created_at else None,
                    "user": {
                        "id": str(like.user.id),
                        "username": like.user.username,
                        "name": like.user.full_name,
                        "image": like.user.image
                    } if like.user else None
                }
                for like in (post.likes[:20] if post.likes else [])  # Limit to first 20 likes
            ],
            "sharesDetails": [
                {
                    "id": str(share.id),
                    "platform": share.platform,
                    "createdAt": share.created_at.isoformat() if share.created_at else None,
                    "user": {
                        "id": str(share.user.id),
                        "username": share.user.username,
                        "name": share.user.full_name
                    } if share.user else None
                }
                for share in post.shares
            ] if post.shares else []
        }
    }
    
    return post_data


@router.post("/", response_model=PostResponse)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new post"""
    return await post_crud.create_post(db=db, post=post, user_id=current_user.id)


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update post"""
    post = await post_crud.get_post(db, post_id=post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user owns the post or has admin privileges
    if post.user_id != current_user.id:
        # You can add admin role check here
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    updated_post = await post_crud.update_post(db=db, post_id=post_id, post_update=post_update)
    return updated_post


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete post"""
    post = await post_crud.get_post(db, post_id=post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user owns the post or has admin privileges
    if post.user_id != current_user.id:
        # You can add admin role check here
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    success = await post_crud.delete_post(db=db, post_id=post_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete post")
    
    return {"message": "Post deleted successfully"}


@router.post("/like")
async def toggle_post_like(
    like_data: LikeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle like/unlike for a post
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
        
        # Toggle the like
        result = await like_crud.toggle_like(
            db=db,
            like_data=like_data,
            ip_address=ip_address
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle like: {str(e)}")


@router.post("/view")
async def record_post_view(
    view_data: ViewCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Record a view for a post
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
        
        # Record the view
        result = await view_crud.record_view(
            db=db,
            view_data=view_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record view: {str(e)}")


@router.get("/like/status")
async def check_post_like_status(
    post_id: int = Query(..., description="Post ID"),
    user_id: Optional[int] = Query(None, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user has liked a post
    """
    try:
        result = await like_crud.check_like_status(
            db=db,
            post_id=post_id,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check like status: {str(e)}")
