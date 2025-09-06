from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, delete
from sqlalchemy.orm import selectinload
import json
import uuid
import os
import re
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Post, PostAttribute, Comment, Like, Share, View, Upload, Tag, Category
from app.services import upload_file_with_fallback

router = APIRouter()


@router.get("/posts", response_model=Dict[str, Any])
async def get_admin_posts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of posts per page"),
    status: Optional[str] = Query(None, description="Filter by post status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    search: Optional[str] = Query(None, description="Search in title and body"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get posts for admin panel with pagination and filtering"""
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Base query with comprehensive relationship loading
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
    
    # Join with PostAttribute for filtering
    query = query.join(PostAttribute)
    
    # Apply filters
    conditions = []
    
    # Status filter
    if status:
        conditions.append(PostAttribute.status == status)
    
    # User filter
    if user_id:
        conditions.append(Post.user_id == user_id)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        conditions.append(
            (Post.title.ilike(search_term)) | 
            (Post.body.ilike(search_term))
        )
    
    # Apply all conditions
    if conditions:
        for condition in conditions:
            query = query.where(condition)
    
    # Get total count for pagination
    count_query = select(func.count(Post.id)).join(PostAttribute)
    if conditions:
        for condition in conditions:
            count_query = count_query.where(condition)
    
    total_result = await db.execute(count_query)
    total_posts = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(Post.id)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    # Process posts into compressed format
    posts_data = []
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
            content["description"] = post.description
        elif post.type == "audio":
            # Get audio URL from uploads
            audio_upload = next((upload for upload in post.uploads if upload.type == "audio"), None)
            content["audioUrl"] = audio_upload.url if audio_upload else None
            content["duration"] = "15:30"  # You might want to store this in post or upload
            content["audioDescription"] = post.caption or post.body
            content["description"] = post.description
        elif post.type == "quote":
            content["quote"] = post.quote
            content["source"] = post.quote_source
        elif post.type == "link":
            content["url"] = post.link_url
            content["linkTitle"] = post.title
            content["linkDescription"] = post.body or post.caption
            content["linkThumbnail"] = post.thumbnail
            content["description"] = post.description
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
            content["description"] = post.description
        
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
            "slug": post.attributes.slug if post.attributes else None,
            "scheduledDate": post.attributes.scheduled_at.isoformat() if post.attributes and post.attributes.scheduled_at else None,
            "allowComments": post.attributes.allow_comments if post.attributes else True,
            "commentStatus": "open" if (post.attributes and post.attributes.allow_comments) else "closed",
            "visibility": post.attributes.visibility if post.attributes else "public",
            "visibilityGroups": json.loads(post.attributes.visibility_groups) if (post.attributes and post.attributes.visibility_groups) else [],
            "isOriginalWork": post.attributes.original_work == "True" if (post.attributes and post.attributes.original_work) else True,
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
        
        posts_data.append(post_data)
    
    # Calculate pagination metadata
    total_pages = (total_posts + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        "data": posts_data,
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalPosts": total_posts,
            "limit": limit,
            "hasNext": has_next,
            "hasPrevious": has_previous,
            "nextPage": page + 1 if has_next else None,
            "previousPage": page - 1 if has_previous else None
        },
        "filters": {
            "status": status,
            "userId": user_id,
            "search": search
        }
    }


@router.get("/posts/all", response_model=Dict[str, Any])
async def get_all_admin_posts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Number of posts per page"),
    status: Optional[str] = Query(None, description="Filter by post status"),
    search: Optional[str] = Query(None, description="Search in title"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all posts in simplified format for admin selection/listing"""
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Base query with minimal relationship loading for performance
    query = select(Post).options(
        selectinload(Post.user),
        selectinload(Post.tags),
        selectinload(Post.attributes)
    )
    
    # Join with PostAttribute for filtering
    query = query.join(PostAttribute)
    
    # Apply filters
    conditions = []
    
    # Status filter
    if status:
        conditions.append(PostAttribute.status == status)
    
    # Search filter (only in title for performance)
    if search:
        search_term = f"%{search}%"
        conditions.append(Post.title.ilike(search_term))
    
    # Apply all conditions
    if conditions:
        for condition in conditions:
            query = query.where(condition)
    
    # Get total count for pagination
    count_query = select(func.count(Post.id)).join(PostAttribute)
    if conditions:
        for condition in conditions:
            count_query = count_query.where(condition)
    
    total_result = await db.execute(count_query)
    total_posts = total_result.scalar()
    
    # Apply pagination and ordering (most recent first)
    query = query.order_by(desc(PostAttribute.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    # Process posts into simplified format
    posts_data = []
    for post in posts:
        post_data = {
            "id": f"post_{post.id}",
            "title": post.title,
            "author": {
                "name": post.user.full_name if post.user and post.user.full_name else (post.user.username if post.user else "Unknown"),
                "avatar": post.user.image if post.user else None
            },
            "createdAt": post.attributes.created_at.isoformat() if post.attributes and post.attributes.created_at else None,
            "status": post.attributes.status if post.attributes else "draft",
            "tags": [tag.name for tag in post.tags] if post.tags else []
        }
        posts_data.append(post_data)
    
    # Calculate pagination metadata
    total_pages = (total_posts + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        "data": posts_data,
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalPosts": total_posts,
            "limit": limit,
            "hasNext": has_next,
            "hasPrevious": has_previous,
            "nextPage": page + 1 if has_next else None,
            "previousPage": page - 1 if has_previous else None
        },
        "filters": {
            "status": status,
            "search": search
        }
    }



@router.get("/posts/{post_id}", response_model=Dict[str, Any])
async def get_admin_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single post for admin panel in compressed format"""
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
        images = [upload.url for upload in post.uploads if upload.type == "image"]
        content["images"] = images
        content["caption"] = post.caption
    elif post.type == "video":
        video_upload = next((upload for upload in post.uploads if upload.type == "video"), None)
        content["videoUrl"] = video_upload.url if video_upload else None
        content["videoThumbnail"] = post.thumbnail
        content["caption"] = post.caption
        content["description"] = post.description
    elif post.type == "audio":
        audio_upload = next((upload for upload in post.uploads if upload.type == "audio"), None)
        content["audioUrl"] = audio_upload.url if audio_upload else None
        content["duration"] = "15:30"
        content["audioDescription"] = post.caption or post.body
        content["description"] = post.description
    elif post.type == "quote":
        content["quote"] = post.quote
        content["source"] = post.quote_source
    elif post.type == "link":
        content["url"] = post.link_url
        content["linkTitle"] = post.title
        content["linkDescription"] = post.body or post.caption
        content["linkThumbnail"] = post.thumbnail
        content["description"] = post.description
    elif post.type == "file":
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
        content["description"] = post.description

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
        "slug": post.attributes.slug if post.attributes else None,
        "scheduledDate": post.attributes.scheduled_at.isoformat() if post.attributes and post.attributes.scheduled_at else None,
        "allowComments": post.attributes.allow_comments if post.attributes else True,
        "commentStatus": "open" if (post.attributes and post.attributes.allow_comments) else "closed",
        "visibility": post.attributes.visibility if post.attributes else "public",
        "visibilityGroups": json.loads(post.attributes.visibility_groups) if (post.attributes and post.attributes.visibility_groups) else [],
        "isOriginalWork": post.attributes.original_work == "True" if (post.attributes and post.attributes.original_work) else True,
        "rightsHolder": post.attributes.rights_holder if post.attributes else None,
        "license": post.attributes.license if post.attributes else "All Rights Reserved",
        "tags": [tag.name for tag in post.tags] if post.tags else [],
        "category": post.category.name if post.category else None,
        "likes": len(post.likes) if post.likes else 0,
        "shares": len(post.shares) if post.shares else 0,
        "saves": 0,
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
                "parentId": str(comment.parent_id) if comment.parent_id else None
            }
            for comment in post.comments
        ] if post.comments else [],
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
                for like in (post.likes[:20] if post.likes else [])
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




@router.get("/posts/stats", response_model=Dict[str, Any])
async def get_posts_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get posts statistics for admin dashboard"""
    
    # Total posts
    total_posts_result = await db.execute(select(func.count(Post.id)))
    total_posts = total_posts_result.scalar()
    
    # Posts by status
    status_query = select(
        PostAttribute.status,
        func.count(Post.id).label('count')
    ).join(PostAttribute).group_by(PostAttribute.status)
    
    status_result = await db.execute(status_query)
    posts_by_status = {row.status: row.count for row in status_result}
    
    # Posts by type
    type_query = select(
        Post.type,
        func.count(Post.id).label('count')
    ).group_by(Post.type)
    
    type_result = await db.execute(type_query)
    posts_by_type = {row.type: row.count for row in type_result}
    
    # Recent activity (posts created in last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_posts_result = await db.execute(
        select(func.count(Post.id))
        .join(PostAttribute)
        .where(PostAttribute.created_at >= thirty_days_ago)
    )
    recent_posts = recent_posts_result.scalar()
    
    return {
        "totalPosts": total_posts,
        "postsByStatus": posts_by_status,
        "postsByType": posts_by_type,
        "recentPosts": recent_posts,
        "generatedAt": datetime.utcnow().isoformat()
    }


# Helper functions for post creation
def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with UUID prefix"""
    ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return unique_name


async def save_upload_file(file: UploadFile, upload_type: str) -> tuple[str, dict]:
    """Save uploaded file using Cloudinary with local fallback and return file URL and metadata"""
    if not file:
        return None, {}
    
    try:
        # Use Cloudinary service with fallback
        file_url, metadata = await upload_file_with_fallback(file, f"uploads/{upload_type}")
        return file_url, metadata
    except Exception as e:
        # Final fallback to local storage
        upload_dir = Path("uploads") / upload_type
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return str(file_path), {'is_cloudinary': False, 'local_path': str(file_path)}


async def handle_category(category_name: str, user_id: int, db: AsyncSession) -> Optional[int]:
    """Handle category lookup/creation"""
    if not category_name or category_name.strip() == "":
        return None
    
    category_name = category_name.strip()
    
    # Look for existing category (case-insensitive)
    result = await db.execute(
        select(Category).where(Category.name.ilike(category_name))
    )
    existing_category = result.scalar_one_or_none()
    
    if existing_category:
        return existing_category.id
    
    # Create new category
    slug = slugify(category_name)
    # Ensure slug is unique
    base_slug = slug
    counter = 1
    while True:
        result = await db.execute(
            select(Category).where(Category.slug == slug)
        )
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    new_category = Category(
        name=category_name,
        slug=slug,
        user_id=user_id
    )
    db.add(new_category)
    await db.flush()
    return new_category.id


async def generate_unique_url(title: str, custom_slug: str, db: AsyncSession) -> str:
    """Generate unique URL for post"""
    if custom_slug:
        slug = slugify(custom_slug)
    else:
        slug = slugify(title)
    
    # Ensure uniqueness
    base_slug = slug
    counter = 1
    while True:
        result = await db.execute(
            select(Post).where(Post.url == slug)
        )
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


async def handle_tags(post_id: int, tag_names: List[str], user_id: int, db: AsyncSession):
    """Handle tag creation for post"""
    for tag_name in tag_names:
        if tag_name.strip():
            tag = Tag(
                post_id=post_id,
                user_id=user_id,
                name=tag_name.strip()
            )
            db.add(tag)


async def create_upload_record(file_path: str, original_filename: str, file_size: int, 
                             upload_type: str, user_id: int, post_id: int, db: AsyncSession, metadata: dict = None) -> Upload:
    """Create upload record in database"""
    mime_type, _ = mimetypes.guess_type(original_filename)
    
    # Use file_path as-is since it's already the full URL for Cloudinary or relative path for local
    upload_url = file_path if file_path.startswith('http') else f"/{file_path}"
    
    upload = Upload(
        url=upload_url,
        user_id=user_id,
        post_id=post_id,
        type=upload_type,
        size=file_size,
        name=original_filename,
        mime_type=mime_type or "application/octet-stream",
        metadata=json.dumps(metadata) if metadata else None
    )
    db.add(upload)
    return upload


def map_content_to_post_fields(post_type: str, content: dict) -> dict:
    """Map content object to post table fields"""
    post_fields = {}
    
    if post_type == "text":
        post_fields["body"] = content.get("body")
    elif post_type == "photo":
        post_fields["caption"] = content.get("caption")
    elif post_type == "video":
        post_fields["caption"] = content.get("caption")
        post_fields["description"] = content.get("description")
        post_fields["thumbnail"] = content.get("videoThumbnail")
    elif post_type == "audio":
        post_fields["description"] = content.get("description")
        post_fields["caption"] = content.get("audioDescription")
    elif post_type == "quote":
        post_fields["quote"] = content.get("quote")
        post_fields["quote_source"] = content.get("source")
    elif post_type == "link":
        post_fields["link_url"] = content.get("url")
        post_fields["description"] = content.get("description")
        post_fields["thumbnail"] = content.get("linkThumbnail")
    elif post_type == "file":
        post_fields["description"] = content.get("description")
    
    return post_fields


@router.post("/posts", response_model=Dict[str, Any])
async def create_admin_post(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new post - handles both JSON and multipart/form-data"""
    
    content_type = request.headers.get("content-type", "")
    
    try:
        # Detect request type and parse accordingly
        if "multipart/form-data" in content_type:
            # Handle multipart form data (posts with files)
            form = await request.form()
            
            # Parse JSON data from form
            data_str = form.get("data")
            if not data_str:
                raise HTTPException(status_code=400, detail="Missing 'data' field in form")
            
            try:
                post_data = json.loads(data_str)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in 'data' field")
            
            # Extract file uploads
            imageFiles = form.getlist("imageFiles") if "imageFiles" in form else None
            videoFile = form.get("videoFile") if "videoFile" in form else None
            audioFile = form.get("audioFile") if "audioFile" in form else None
            files = form.getlist("files") if "files" in form else None
            posterImage = form.get("posterImage") if "posterImage" in form else None
            captionFile = form.get("captionFile") if "captionFile" in form else None
            captionFiles = form.getlist("captionFiles") if "captionFiles" in form else None
            
        else:
            # Handle JSON request (text-only posts)
            post_data = await request.json()
            
            # No files for JSON requests
            imageFiles = None
            videoFile = None
            audioFile = None
            files = None
            posterImage = None
            captionFile = None
            captionFiles = None
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error parsing request: {str(e)}")
    
    # Validate required fields
    if not post_data.get("title"):
        raise HTTPException(status_code=400, detail="Title is required")
    
    if not post_data.get("type"):
        raise HTTPException(status_code=400, detail="Post type is required")
    
    if post_data["type"] not in ["text", "quote", "link", "photo", "file", "audio", "video"]:
        raise HTTPException(status_code=400, detail="Invalid post type")
    
    content = post_data.get("content", {})
    
    # Type-specific validation
    if post_data["type"] == "text" and not content.get("body"):
        raise HTTPException(status_code=400, detail="Body is required for text posts")
    
    if post_data["type"] == "quote" and not content.get("quote"):
        raise HTTPException(status_code=400, detail="Quote is required for quote posts")
    
    if post_data["type"] == "link" and not content.get("url"):
        raise HTTPException(status_code=400, detail="URL is required for link posts")
    
    # File validation only for multipart requests
    if "multipart/form-data" in content_type:
        if post_data["type"] == "photo" and not imageFiles:
            raise HTTPException(status_code=400, detail="Image files are required for photo posts")
        
        # For video posts, check if either videoFile is provided (for uploads) or videoUrl is provided (for URL videos)
        if post_data["type"] == "video":
            has_video_file = videoFile and hasattr(videoFile, 'filename') and videoFile.filename
            has_video_url = content.get("videoUrl")
            if not has_video_file and not has_video_url:
                raise HTTPException(status_code=400, detail="Either video file or video URL is required for video posts")
        
        if post_data["type"] == "audio" and not audioFile:
            raise HTTPException(status_code=400, detail="Audio file is required for audio posts")
        
        if post_data["type"] == "file" and not files:
            raise HTTPException(status_code=400, detail="Files are required for file posts")
    else:
        # For JSON requests, only URL-based videos are allowed
        if post_data["type"] == "video" and not content.get("videoUrl"):
            raise HTTPException(status_code=400, detail="Video URL is required for video posts in JSON requests")
    
    try:
        # Handle category
        category_id = await handle_category(
            post_data.get("category"), 
            current_user.id, 
            db
        )
        
        # Generate unique URL
        post_url = await generate_unique_url(
            post_data["title"], 
            post_data.get("slug"), 
            db
        )
        
        # Map content to post fields
        post_fields = map_content_to_post_fields(post_data["type"], content)
        
        # Handle video URL for URL-type videos (when videoUrl is provided but no video file)
        if post_data["type"] == "video" and content.get("videoUrl") and not videoFile:
            post_fields["link_url"] = content.get("videoUrl")
        
        # Create post record
        post = Post(
            title=post_data["title"],
            type=post_data["type"],
            url=post_url,
            user_id=current_user.id,
            category_id=category_id,
            **post_fields
        )
        
        db.add(post)
        await db.flush()  # Get post ID
        
        # Create post attributes
        # Parse scheduledDate if provided
        scheduled_at = None
        if post_data.get("scheduledDate"):
            try:
                scheduled_at = datetime.fromisoformat(post_data["scheduledDate"].replace('Z', '+00:00'))
            except ValueError:
                pass  # Invalid date format, ignore
        
        # Parse allowComments from commentStatus
        allow_comments = True  # Default
        if post_data.get("commentStatus"):
            allow_comments = post_data["commentStatus"] == "open"
        elif "allowComments" in post_data:
            allow_comments = post_data.get("allowComments", True)
        
        # Handle visibility groups (convert list to JSON string)
        visibility_groups = None
        if post_data.get("visibilityGroups"):
            visibility_groups = json.dumps(post_data["visibilityGroups"])
        
        attributes = PostAttribute(
            post_id=post.id,
            status=post_data.get("status", "draft"),
            pinned=post_data.get("isPinned", False),
            slug=post_url,
            scheduled_at=scheduled_at,
            allow_comments=allow_comments,
            visibility=post_data.get("visibility", "public"),
            visibility_groups=visibility_groups,
            original_work=str(post_data.get("isOriginalWork", True)) if "isOriginalWork" in post_data else None,
            rights_holder=post_data.get("rightsHolder"),
            license=post_data.get("license", "All Rights Reserved")
        )
        db.add(attributes)
        
        # Handle tags
        if post_data.get("tags"):
            await handle_tags(post.id, post_data["tags"], current_user.id, db)
        
        # Process file uploads based on post type (only for multipart requests)
        uploaded_files = []
        
        if "multipart/form-data" in content_type:
            if post_data["type"] == "photo" and imageFiles:
                for image_file in imageFiles:
                    if hasattr(image_file, 'filename') and image_file.filename:
                        file_path, metadata = await save_upload_file(image_file, "images")
                        upload = await create_upload_record(
                            file_path, image_file.filename, 
                            getattr(image_file, 'size', 0), "image",
                            current_user.id, post.id, db, metadata
                        )
                        uploaded_files.append(upload)
            
            elif post_data["type"] == "video" and videoFile:
                if hasattr(videoFile, 'filename') and videoFile.filename:
                    file_path, metadata = await save_upload_file(videoFile, "videos")
                    upload = await create_upload_record(
                        file_path, videoFile.filename,
                        getattr(videoFile, 'size', 0), "video",
                        current_user.id, post.id, db, metadata
                    )
                    uploaded_files.append(upload)
                    
                    # Set the video URL in the post record for easy access
                    post.link_url = file_path if file_path.startswith('http') else f"/{file_path}"
            
            elif post_data["type"] == "audio" and audioFile:
                if hasattr(audioFile, 'filename') and audioFile.filename:
                    file_path, metadata = await save_upload_file(audioFile, "audio")
                    upload = await create_upload_record(
                        file_path, audioFile.filename,
                        getattr(audioFile, 'size', 0), "audio",
                        current_user.id, post.id, db, metadata
                    )
                    uploaded_files.append(upload)
            
            elif post_data["type"] == "file" and files:
                for file in files:
                    if hasattr(file, 'filename') and file.filename:
                        file_path, metadata = await save_upload_file(file, "files")
                        upload = await create_upload_record(
                            file_path, file.filename,
                            getattr(file, 'size', 0), "file",
                            current_user.id, post.id, db, metadata
                        )
                        uploaded_files.append(upload)
            
            # Handle poster image for videos
            if posterImage and hasattr(posterImage, 'filename') and posterImage.filename:
                file_path, metadata = await save_upload_file(posterImage, "images")
                upload = await create_upload_record(
                    file_path, posterImage.filename,
                    getattr(posterImage, 'size', 0), "image",
                    current_user.id, post.id, db, metadata
                )
                uploaded_files.append(upload)
                
                # Set thumbnail path in post
                post.thumbnail = file_path if file_path.startswith('http') else f"/{file_path}"
            
            # Handle caption files
            if captionFile and hasattr(captionFile, 'filename') and captionFile.filename:
                file_path, metadata = await save_upload_file(captionFile, "captions")
                upload = await create_upload_record(
                    file_path, captionFile.filename,
                    getattr(captionFile, 'size', 0), "caption",
                    current_user.id, post.id, db, metadata
                )
                uploaded_files.append(upload)
            
            if captionFiles:
                for caption_file in captionFiles:
                    if hasattr(caption_file, 'filename') and caption_file.filename:
                        file_path, metadata = await save_upload_file(caption_file, "captions")
                        upload = await create_upload_record(
                            file_path, caption_file.filename,
                            getattr(caption_file, 'size', 0), "caption",
                            current_user.id, post.id, db, metadata
                        )
                        uploaded_files.append(upload)
        
        await db.commit()
        
        # Return the created post in the same format as other endpoints
        return {
            "id": str(post.id),
            "title": post.title,
            "type": post.type,
            "url": post.url,
            "status": attributes.status,
            "slug": attributes.slug,
            "pinned": attributes.pinned,
            "createdAt": attributes.created_at.isoformat(),
            "author": {
                "id": str(current_user.id),
                "username": current_user.username,
                "name": current_user.full_name,
                "image": current_user.image
            },
            "category": category_id,
            "tags": post_data.get("tags", []),
            "uploads": [
                {
                    "id": str(upload.id),
                    "url": upload.url,
                    "name": upload.name,
                    "type": upload.type,
                    "size": upload.size,
                    "mimeType": upload.mime_type
                }
                for upload in uploaded_files
            ],
            "message": "Post created successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error creating post: {str(e)}")


@router.put("/posts/{post_id}", response_model=Dict[str, Any])
async def update_admin_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing post - handles both JSON and multipart/form-data"""
    
    # Check if post exists
    result = await db.execute(
        select(Post).options(
            selectinload(Post.attributes),
            selectinload(Post.uploads),
            selectinload(Post.tags)
        ).where(Post.id == post_id)
    )
    existing_post = result.scalar_one_or_none()
    
    if not existing_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user has permission to edit this post
    # TODO: Add proper permission checking based on user roles
    if existing_post.user_id != current_user.id:
        # For now, only allow the author to edit, later add admin/moderator permissions
        pass  # Allow admin users to edit any post
    
    content_type = request.headers.get("content-type", "")
    
    try:
        # Detect request type and parse accordingly
        if "multipart/form-data" in content_type:
            # Handle multipart form data (posts with files)
            form = await request.form()
            
            # Parse JSON data from form
            data_str = form.get("data")
            if not data_str:
                raise HTTPException(status_code=400, detail="Missing 'data' field in form")
            
            try:
                post_data = json.loads(data_str)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in 'data' field")
            
            # Extract file uploads
            imageFiles = form.getlist("imageFiles") if "imageFiles" in form else None
            videoFile = form.get("videoFile") if "videoFile" in form else None
            audioFile = form.get("audioFile") if "audioFile" in form else None
            files = form.getlist("files") if "files" in form else None
            posterImage = form.get("posterImage") if "posterImage" in form else None
            captionFile = form.get("captionFile") if "captionFile" in form else None
            captionFiles = form.getlist("captionFiles") if "captionFiles" in form else None
            
        else:
            # Handle JSON request (text-only posts)
            post_data = await request.json()
            
            # No files for JSON requests
            imageFiles = None
            videoFile = None
            audioFile = None
            files = None
            posterImage = None
            captionFile = None
            captionFiles = None
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Error parsing request: {str(e)}")
    
    # Validate post type if it's being changed
    if post_data.get("type") and post_data["type"] not in ["text", "quote", "link", "photo", "file", "audio", "video"]:
        raise HTTPException(status_code=400, detail="Invalid post type")
    
    content = post_data.get("content", {})
    post_type = post_data.get("type", existing_post.type)
    
    # Type-specific validation
    if post_type == "text" and content.get("body") == "":
        raise HTTPException(status_code=400, detail="Body cannot be empty for text posts")
    
    if post_type == "quote" and content.get("quote") == "":
        raise HTTPException(status_code=400, detail="Quote cannot be empty for quote posts")
    
    if post_type == "link" and content.get("url") == "":
        raise HTTPException(status_code=400, detail="URL cannot be empty for link posts")
    
    # For video posts, validate based on what's provided
    if post_type == "video":
        has_video_file = videoFile and hasattr(videoFile, 'filename') and videoFile.filename
        has_video_url = content.get("videoUrl")
        # If updating and neither file nor URL provided, that's okay (keep existing)
        # But if one is provided and empty, that's an error
        if content.get("videoUrl") == "":
            raise HTTPException(status_code=400, detail="Video URL cannot be empty if provided")
    
    try:
        # Handle category update
        category_id = existing_post.category_id
        if "category" in post_data:
            category_id = await handle_category(
                post_data.get("category"), 
                current_user.id, 
                db
            )
        
        # Generate unique URL if title or slug changed
        post_url = existing_post.url
        if post_data.get("title") or post_data.get("slug"):
            new_title = post_data.get("title", existing_post.title)
            new_slug = post_data.get("slug")
            
            # Only generate new URL if it's different
            new_url = await generate_unique_url(new_title, new_slug, db)
            if new_url != existing_post.url:
                post_url = new_url
        
        # Update post fields
        if post_data.get("title"):
            existing_post.title = post_data["title"]
        
        if post_data.get("type"):
            existing_post.type = post_data["type"]
        
        existing_post.url = post_url
        
        if category_id is not None:
            existing_post.category_id = category_id
        
        # Map content to post fields
        if content:
            post_fields = map_content_to_post_fields(post_type, content)
            
            # Update only provided content fields
            for field, value in post_fields.items():
                if value is not None:
                    setattr(existing_post, field, value)
        
        # Handle video URL for URL-type videos (when videoUrl is provided but no video file)
        if post_type == "video" and content.get("videoUrl") and not videoFile:
            existing_post.link_url = content.get("videoUrl")
        
        # Update post attributes
        if existing_post.attributes:
            if "status" in post_data:
                existing_post.attributes.status = post_data["status"]
            
            if "isPinned" in post_data:
                existing_post.attributes.pinned = post_data["isPinned"]
            
            # Handle scheduledDate
            if "scheduledDate" in post_data:
                if post_data["scheduledDate"]:
                    try:
                        existing_post.attributes.scheduled_at = datetime.fromisoformat(
                            post_data["scheduledDate"].replace('Z', '+00:00')
                        )
                    except ValueError:
                        pass  # Invalid date format, ignore
                else:
                    existing_post.attributes.scheduled_at = None
            
            # Handle allowComments from commentStatus or direct field
            if "commentStatus" in post_data:
                existing_post.attributes.allow_comments = post_data["commentStatus"] == "open"
            elif "allowComments" in post_data:
                existing_post.attributes.allow_comments = post_data["allowComments"]
            
            # Handle visibility fields
            if "visibility" in post_data:
                existing_post.attributes.visibility = post_data["visibility"]
            
            if "visibilityGroups" in post_data:
                if post_data["visibilityGroups"]:
                    existing_post.attributes.visibility_groups = json.dumps(post_data["visibilityGroups"])
                else:
                    existing_post.attributes.visibility_groups = None
            
            # Handle copyright fields
            if "isOriginalWork" in post_data:
                existing_post.attributes.original_work = str(post_data["isOriginalWork"])
            
            if "rightsHolder" in post_data:
                existing_post.attributes.rights_holder = post_data["rightsHolder"]
            
            if "license" in post_data:
                existing_post.attributes.license = post_data["license"]
            
            existing_post.attributes.slug = post_url
            existing_post.attributes.updated_at = datetime.utcnow()
        else:
            # Create attributes if they don't exist
            # Parse scheduledDate if provided
            scheduled_at = None
            if post_data.get("scheduledDate"):
                try:
                    scheduled_at = datetime.fromisoformat(post_data["scheduledDate"].replace('Z', '+00:00'))
                except ValueError:
                    pass  # Invalid date format, ignore
            
            # Parse allowComments from commentStatus
            allow_comments = True  # Default
            if post_data.get("commentStatus"):
                allow_comments = post_data["commentStatus"] == "open"
            elif "allowComments" in post_data:
                allow_comments = post_data.get("allowComments", True)
            
            # Handle visibility groups (convert list to JSON string)
            visibility_groups = None
            if post_data.get("visibilityGroups"):
                visibility_groups = json.dumps(post_data["visibilityGroups"])
            
            attributes = PostAttribute(
                post_id=existing_post.id,
                status=post_data.get("status", "draft"),
                pinned=post_data.get("isPinned", False),
                slug=post_url,
                scheduled_at=scheduled_at,
                allow_comments=allow_comments,
                visibility=post_data.get("visibility", "public"),
                visibility_groups=visibility_groups,
                original_work=str(post_data.get("isOriginalWork", True)) if "isOriginalWork" in post_data else None,
                rights_holder=post_data.get("rightsHolder"),
                license=post_data.get("license", "All Rights Reserved")
            )
            db.add(attributes)
        
        # Handle tags update
        if "tags" in post_data:
            # Remove existing tags using direct delete
            await db.execute(
                delete(Tag).where(Tag.post_id == existing_post.id)
            )
            
            # Flush to ensure deletion is committed before adding new tags
            await db.flush()
            
            # Add new tags
            if post_data["tags"]:
                await handle_tags(existing_post.id, post_data["tags"], current_user.id, db)
        
        # Handle file uploads (only for multipart requests)
        new_uploaded_files = []
        
        if "multipart/form-data" in content_type:
            # Handle new file uploads based on post type
            if post_type == "photo" and imageFiles:
                for image_file in imageFiles:
                    if hasattr(image_file, 'filename') and image_file.filename:
                        file_path, metadata = await save_upload_file(image_file, "images")
                        upload = await create_upload_record(
                            file_path, image_file.filename, 
                            getattr(image_file, 'size', 0), "image",
                            current_user.id, existing_post.id, db, metadata
                        )
                        new_uploaded_files.append(upload)
            
            elif post_type == "video" and videoFile:
                if hasattr(videoFile, 'filename') and videoFile.filename:
                    file_path, metadata = await save_upload_file(videoFile, "videos")
                    upload = await create_upload_record(
                        file_path, videoFile.filename,
                        getattr(videoFile, 'size', 0), "video",
                        current_user.id, existing_post.id, db, metadata
                    )
                    new_uploaded_files.append(upload)
                    
                    # Set the video URL in the post record for easy access
                    existing_post.link_url = file_path if file_path.startswith('http') else f"/{file_path}"
            
            elif post_type == "audio" and audioFile:
                if hasattr(audioFile, 'filename') and audioFile.filename:
                    file_path, metadata = await save_upload_file(audioFile, "audio")
                    upload = await create_upload_record(
                        file_path, audioFile.filename,
                        getattr(audioFile, 'size', 0), "audio",
                        current_user.id, existing_post.id, db, metadata
                    )
                    new_uploaded_files.append(upload)
            
            elif post_type == "file" and files:
                for file in files:
                    if hasattr(file, 'filename') and file.filename:
                        file_path, metadata = await save_upload_file(file, "files")
                        upload = await create_upload_record(
                            file_path, file.filename,
                            getattr(file, 'size', 0), "file",
                            current_user.id, existing_post.id, db, metadata
                        )
                        new_uploaded_files.append(upload)
            
            # Handle poster image for videos
            if posterImage and hasattr(posterImage, 'filename') and posterImage.filename:
                file_path, metadata = await save_upload_file(posterImage, "images")
                upload = await create_upload_record(
                    file_path, posterImage.filename,
                    getattr(posterImage, 'size', 0), "image",
                    current_user.id, existing_post.id, db, metadata
                )
                new_uploaded_files.append(upload)
                
                # Set thumbnail path in post
                existing_post.thumbnail = file_path if file_path.startswith('http') else f"/{file_path}"
            
            # Handle caption files
            if captionFile and hasattr(captionFile, 'filename') and captionFile.filename:
                file_path, metadata = await save_upload_file(captionFile, "captions")
                upload = await create_upload_record(
                    file_path, captionFile.filename,
                    getattr(captionFile, 'size', 0), "caption",
                    current_user.id, existing_post.id, db, metadata
                )
                new_uploaded_files.append(upload)
            
            if captionFiles:
                for caption_file in captionFiles:
                    if hasattr(caption_file, 'filename') and caption_file.filename:
                        file_path, metadata = await save_upload_file(caption_file, "captions")
                        upload = await create_upload_record(
                            file_path, caption_file.filename,
                            getattr(caption_file, 'size', 0), "caption",
                            current_user.id, existing_post.id, db, metadata
                        )
                        new_uploaded_files.append(upload)
        
        await db.commit()
        
        # Reload the updated post with all relationships
        result = await db.execute(
            select(Post).options(
                selectinload(Post.user),
                selectinload(Post.attributes),
                selectinload(Post.uploads),
                selectinload(Post.tags),
                selectinload(Post.category)
            ).where(Post.id == post_id)
        )
        updated_post = result.scalar_one()
        
        # Return the updated post in the same format as other endpoints
        return {
            "id": str(updated_post.id),
            "title": updated_post.title,
            "type": updated_post.type,
            "url": updated_post.url,
            "status": updated_post.attributes.status if updated_post.attributes else "draft",
            "slug": updated_post.attributes.slug if updated_post.attributes else updated_post.url,
            "pinned": updated_post.attributes.pinned if updated_post.attributes else False,
            "createdAt": updated_post.attributes.created_at.isoformat() if updated_post.attributes and updated_post.attributes.created_at else None,
            "updatedAt": updated_post.attributes.updated_at.isoformat() if updated_post.attributes and updated_post.attributes.updated_at else None,
            "author": {
                "id": str(updated_post.user.id),
                "username": updated_post.user.username,
                "name": updated_post.user.full_name,
                "image": updated_post.user.image
            } if updated_post.user else None,
            "category": updated_post.category.name if updated_post.category else None,
            "tags": [tag.name for tag in updated_post.tags] if updated_post.tags else [],
            "uploads": [
                {
                    "id": str(upload.id),
                    "url": upload.url,
                    "name": upload.name,
                    "type": upload.type,
                    "size": upload.size,
                    "mimeType": upload.mime_type
                }
                for upload in updated_post.uploads
            ],
            "newUploads": [
                {
                    "id": str(upload.id),
                    "url": upload.url,
                    "name": upload.name,
                    "type": upload.type,
                    "size": upload.size,
                    "mimeType": upload.mime_type
                }
                for upload in new_uploaded_files
            ],
            "message": "Post updated successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error updating post: {str(e)}")


@router.delete("/posts/{post_id}", response_model=Dict[str, Any])
async def delete_admin_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a post and all its associated data"""
    
    # Check if post exists
    result = await db.execute(
        select(Post).options(
            selectinload(Post.attributes),
            selectinload(Post.uploads),
            selectinload(Post.tags),
            selectinload(Post.comments),
            selectinload(Post.likes),
            selectinload(Post.shares),
            selectinload(Post.views)
        ).where(Post.id == post_id)
    )
    existing_post = result.scalar_one_or_none()
    
    if not existing_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user has permission to delete this post
    # TODO: Add proper permission checking based on user roles
    if existing_post.user_id != current_user.id:
        # For now, only allow the author to delete, later add admin/moderator permissions
        pass  # Allow admin users to delete any post
    
    try:
        # Delete associated files from filesystem
        deleted_files = []
        if existing_post.uploads:
            for upload in existing_post.uploads:
                file_path = upload.url.lstrip('/')  # Remove leading slash
                full_path = Path(file_path)
                if full_path.exists():
                    try:
                        full_path.unlink()  # Delete the file
                        deleted_files.append(str(full_path))
                    except OSError as e:
                        # Log the error but continue with database deletion
                        print(f"Warning: Could not delete file {full_path}: {e}")
        
        # Delete thumbnail file if it exists and is not already in uploads
        if existing_post.thumbnail:
            thumbnail_path = existing_post.thumbnail.lstrip('/')
            full_thumbnail_path = Path(thumbnail_path)
            # Check if thumbnail is not already handled by uploads deletion
            if full_thumbnail_path.exists() and str(full_thumbnail_path) not in deleted_files:
                try:
                    full_thumbnail_path.unlink()
                    deleted_files.append(str(full_thumbnail_path))
                except OSError as e:
                    print(f"Warning: Could not delete thumbnail {full_thumbnail_path}: {e}")
        
        # Delete all associated database records
        # The relationships should handle cascading deletes, but we'll be explicit
        
        # Delete views
        if existing_post.views:
            await db.execute(delete(View).where(View.post_id == post_id))
        
        # Delete likes
        if existing_post.likes:
            await db.execute(delete(Like).where(Like.post_id == post_id))
        
        # Delete shares
        if existing_post.shares:
            await db.execute(delete(Share).where(Share.post_id == post_id))
        
        # Delete comments (including nested comments)
        if existing_post.comments:
            await db.execute(delete(Comment).where(Comment.post_id == post_id))
        
        # Delete tags
        if existing_post.tags:
            await db.execute(delete(Tag).where(Tag.post_id == post_id))
        
        # Delete uploads
        if existing_post.uploads:
            await db.execute(delete(Upload).where(Upload.post_id == post_id))
        
        # Delete post attributes
        if existing_post.attributes:
            await db.execute(delete(PostAttribute).where(PostAttribute.post_id == post_id))
        
        # Finally, delete the post itself
        await db.execute(delete(Post).where(Post.id == post_id))
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Post deleted successfully",
            "deletedPost": {
                "id": str(existing_post.id),
                "title": existing_post.title,
                "type": existing_post.type,
                "url": existing_post.url
            },
            "deletedFiles": deleted_files,
            "deletedRecords": {
                "views": len(existing_post.views) if existing_post.views else 0,
                "likes": len(existing_post.likes) if existing_post.likes else 0,
                "shares": len(existing_post.shares) if existing_post.shares else 0,
                "comments": len(existing_post.comments) if existing_post.comments else 0,
                "tags": len(existing_post.tags) if existing_post.tags else 0,
                "uploads": len(existing_post.uploads) if existing_post.uploads else 0
            }
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting post: {str(e)}")


# Note: POST, PUT, DELETE routes for posts would be added here
# They are quite large, so I'll add them separately if needed
