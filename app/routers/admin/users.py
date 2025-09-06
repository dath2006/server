from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
from pathlib import Path
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Post, PostAttribute, Comment, Like, Share, View, Upload, Tag, Category

router = APIRouter()


def map_user_role(group_id: int) -> str:
    """Map group ID to user role"""
    role_mapping = {
        1: "admin",
        2: "editor", 
        3: "contributor",
        4: "member",
        5: "member"  # Default group
    }
    return role_mapping.get(group_id, "member")


@router.get("/users", response_model=Dict[str, Any])
async def get_admin_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of users per page"),
    search: Optional[str] = Query(None, description="Search in username, email, or full name"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get users for admin panel with pagination and filtering"""
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Base query with comprehensive relationship loading
    query = select(User).options(
        selectinload(User.group),
        selectinload(User.posts),
        selectinload(User.comments),
        selectinload(User.likes)
    )
    
    # Apply filters
    conditions = []
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        conditions.append(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    # Role filter
    if role:
        role_group_mapping = {
            "admin": [1],      # Admin group
            "member": [2],     # Member group
            "friend": [3],     # Friend group  
            "banned": [4],     # Banned group
            "guest": [5]       # Guest group
        }
        if role in role_group_mapping:
            conditions.append(User.group_id.in_(role_group_mapping[role]))
    
    # Apply all conditions
    if conditions:
        for condition in conditions:
            query = query.where(condition)
    
    # Get total count for pagination
    count_query = select(func.count(User.id))
    if conditions:
        for condition in conditions:
            count_query = count_query.where(condition)
    
    total_result = await db.execute(count_query)
    total_users = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(User.id)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Process users into required format
    users_data = []
    for user in users:
        # Calculate stats
        posts_count = len(user.posts) if user.posts else 0
        comments_count = len(user.comments) if user.comments else 0
        liked_posts_count = len(user.likes) if user.likes else 0
        
        user_data = {
            "id": str(user.id),
            "name": user.full_name or user.username,
            "email": user.email,
            "lastLogin": None,  # TODO: Implement last login tracking
            "createdAt": user.joined_at.isoformat() if user.joined_at else None,
            "role": map_user_role(user.group_id),
            "username": user.username,
            "fullName": user.full_name,
            "website": user.website,
            "image": user.image,
            "approved": user.approved,
            "isActive": user.is_active,
            "stats": {
                "posts": posts_count,
                "comments": comments_count,
                "likedPosts": liked_posts_count
            }
        }
        
        users_data.append(user_data)
    
    # Calculate pagination metadata
    total_pages = (total_users + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        "data": users_data,
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalUsers": total_users,
            "limit": limit,
            "hasNext": has_next,
            "hasPrevious": has_previous,
            "nextPage": page + 1 if has_next else None,
            "previousPage": page - 1 if has_previous else None
        },
        "filters": {
            "search": search,
            "role": role
        }
    }


@router.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_admin_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single user for admin panel"""
    query = select(User).options(
        selectinload(User.group),
        selectinload(User.posts),
        selectinload(User.comments),
        selectinload(User.likes)
    ).where(User.id == user_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate stats
    posts_count = len(user.posts) if user.posts else 0
    comments_count = len(user.comments) if user.comments else 0
    liked_posts_count = len(user.likes) if user.likes else 0

    user_data = {
        "id": str(user.id),
        "name": user.full_name or user.username,
        "email": user.email,
        "lastLogin": None,  # TODO: Implement last login tracking
        "createdAt": user.joined_at.isoformat() if user.joined_at else None,
        "role": map_user_role(user.group_id),
        "username": user.username,
        "fullName": user.full_name,
        "website": user.website,
        "image": user.image,
        "approved": user.approved,
        "isActive": user.is_active,
        "googleId": user.google_id,
        "groupId": user.group_id,
        "stats": {
            "posts": posts_count,
            "comments": comments_count,
            "likedPosts": liked_posts_count
        }
    }
    
    return user_data


@router.post("/users", response_model=Dict[str, Any])
async def create_admin_user(
    user_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new user"""
    
    # Validate required fields
    if not user_data.get("username"):
        raise HTTPException(status_code=400, detail="Username is required")
    
    if not user_data.get("email"):
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Check if username already exists
    existing_username = await db.execute(
        select(User).where(User.username == user_data["username"])
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    existing_email = await db.execute(
        select(User).where(User.email == user_data["email"])
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    try:
        # Map role to group_id
        role_group_mapping = {
            "admin": 1,      # Admin group
            "member": 2,     # Member group (default group for regular users)
            "friend": 3,     # Friend group (trusted users)
            "banned": 4,     # Banned group
            "guest": 5       # Guest group
        }
        group_id = role_group_mapping.get(user_data.get("role", "member"), 2)
        
        # Create user record
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data.get("fullName"),
            website=user_data.get("website"),
            image=user_data.get("image"),
            group_id=group_id,
            approved=user_data.get("approved", True),
            is_active=user_data.get("isActive", True),
            hashed_password=None  # Will be set when user sets password
        )
        
        db.add(user)
        await db.flush()  # Get user ID
        await db.commit()
        
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "fullName": user.full_name,
            "website": user.website,
            "role": map_user_role(user.group_id),
            "approved": user.approved,
            "isActive": user.is_active,
            "createdAt": user.joined_at.isoformat(),
            "message": "User created successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


@router.put("/users/{user_id}", response_model=Dict[str, Any])
async def update_admin_user(
    user_id: int,
    user_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing user"""
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    existing_user = result.scalar_one_or_none()
    
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent users from editing themselves in certain ways (relaxed since all users can access admin now)
    if existing_user.id == current_user.id:
        # Don't allow user to deactivate themselves
        if "isActive" in user_data and not user_data["isActive"]:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        
        # Allow users to change their own role (removed restriction since all users have admin access)
        # if "role" in user_data and user_data["role"] != "admin":
        #     raise HTTPException(status_code=400, detail="Cannot change your own admin role")
    
    try:
        # Check if username is being changed and already exists
        if "username" in user_data and user_data["username"] != existing_user.username:
            existing_username = await db.execute(
                select(User).where(User.username == user_data["username"])
            )
            if existing_username.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Username already exists")
            existing_user.username = user_data["username"]
        
        # Check if email is being changed and already exists
        if "email" in user_data and user_data["email"] != existing_user.email:
            existing_email = await db.execute(
                select(User).where(User.email == user_data["email"])
            )
            if existing_email.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already exists")
            existing_user.email = user_data["email"]
        
        # Update other fields
        if "fullName" in user_data:
            existing_user.full_name = user_data["fullName"]
        
        if "website" in user_data:
            existing_user.website = user_data["website"]
        
        if "image" in user_data:
            existing_user.image = user_data["image"]
        
        if "approved" in user_data:
            existing_user.approved = user_data["approved"]
        
        if "isActive" in user_data:
            existing_user.is_active = user_data["isActive"]
        
        # Handle role change
        if "role" in user_data:
            role_group_mapping = {
                "admin": 1,      # Admin group
                "member": 2,     # Member group (standard users) 
                "friend": 3,     # Friend group (trusted users)
                "banned": 4,     # Banned group
                "guest": 5       # Guest group
            }
            new_group_id = role_group_mapping.get(user_data["role"])
            if new_group_id:
                existing_user.group_id = new_group_id
        
        await db.commit()
        
        # Reload user with relationships for stats
        updated_result = await db.execute(
            select(User).options(
                selectinload(User.posts),
                selectinload(User.comments),
                selectinload(User.likes)
            ).where(User.id == user_id)
        )
        updated_user = updated_result.scalar_one()
        
        # Calculate stats
        posts_count = len(updated_user.posts) if updated_user.posts else 0
        comments_count = len(updated_user.comments) if updated_user.comments else 0
        liked_posts_count = len(updated_user.likes) if updated_user.likes else 0
        
        return {
            "id": str(updated_user.id),
            "username": updated_user.username,
            "email": updated_user.email,
            "fullName": updated_user.full_name,
            "website": updated_user.website,
            "image": updated_user.image,
            "role": map_user_role(updated_user.group_id),
            "approved": updated_user.approved,
            "isActive": updated_user.is_active,
            "createdAt": updated_user.joined_at.isoformat() if updated_user.joined_at else None,
            "stats": {
                "posts": posts_count,
                "comments": comments_count,
                "likedPosts": liked_posts_count
            },
            "message": "User updated successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")


@router.delete("/users/{user_id}", response_model=Dict[str, Any])
async def delete_admin_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a user and handle their associated data"""
    
    # Check if user exists
    result = await db.execute(
        select(User).options(
            selectinload(User.posts),
            selectinload(User.comments),
            selectinload(User.tags),
            selectinload(User.uploads),
            selectinload(User.likes),
            selectinload(User.shares),
            selectinload(User.views),
            selectinload(User.categories)
        ).where(User.id == user_id)
    )
    existing_user = result.scalar_one_or_none()
    
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent users from deleting themselves
    if existing_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    try:
        deleted_counts = {
            "posts": 0,
            "comments": 0,
            "tags": 0,
            "uploads": 0,
            "likes": 0,
            "shares": 0,
            "views": 0,
            "categories": 0,
            "files": 0
        }
        
        # Delete associated files from filesystem
        deleted_files = []
        if existing_user.uploads:
            for upload in existing_user.uploads:
                file_path = upload.url.lstrip('/')  # Remove leading slash
                full_path = Path(file_path)
                if full_path.exists():
                    try:
                        full_path.unlink()
                        deleted_files.append(str(full_path))
                        deleted_counts["files"] += 1
                    except OSError as e:
                        print(f"Warning: Could not delete file {full_path}: {e}")
        
        # Count items before deletion
        if existing_user.posts:
            deleted_counts["posts"] = len(existing_user.posts)
        if existing_user.comments:
            deleted_counts["comments"] = len(existing_user.comments)
        if existing_user.tags:
            deleted_counts["tags"] = len(existing_user.tags)
        if existing_user.uploads:
            deleted_counts["uploads"] = len(existing_user.uploads)
        if existing_user.likes:
            deleted_counts["likes"] = len(existing_user.likes)
        if existing_user.shares:
            deleted_counts["shares"] = len(existing_user.shares)
        if existing_user.views:
            deleted_counts["views"] = len(existing_user.views)
        if existing_user.categories:
            deleted_counts["categories"] = len(existing_user.categories)
        
        # Delete all associated database records
        # The relationships should handle cascading deletes, but we'll be explicit
        
        # Delete user's views
        if existing_user.views:
            await db.execute(delete(View).where(View.user_id == user_id))
        
        # Delete user's likes
        if existing_user.likes:
            await db.execute(delete(Like).where(Like.user_id == user_id))
        
        # Delete user's shares
        if existing_user.shares:
            await db.execute(delete(Share).where(Share.user_id == user_id))
        
        # Delete user's tags
        if existing_user.tags:
            await db.execute(delete(Tag).where(Tag.user_id == user_id))
        
        # Delete user's uploads
        if existing_user.uploads:
            await db.execute(delete(Upload).where(Upload.user_id == user_id))
        
        # Delete user's comments
        if existing_user.comments:
            await db.execute(delete(Comment).where(Comment.user_id == user_id))
        
        # Handle user's posts - we can either delete them or reassign to another user
        # For now, we'll delete them along with their attributes
        if existing_user.posts:
            for post in existing_user.posts:
                # Delete post attributes
                await db.execute(delete(PostAttribute).where(PostAttribute.post_id == post.id))
                # Delete the post itself (other related data should be handled above)
                await db.execute(delete(Post).where(Post.id == post.id))
        
        # Delete user's categories
        if existing_user.categories:
            await db.execute(delete(Category).where(Category.user_id == user_id))
        
        # Finally, delete the user itself
        await db.execute(delete(User).where(User.id == user_id))
        
        await db.commit()
        
        return {
            "success": True,
            "message": "User deleted successfully",
            "deletedUser": {
                "id": str(existing_user.id),
                "username": existing_user.username,
                "email": existing_user.email,
                "fullName": existing_user.full_name
            },
            "deletedFiles": deleted_files,
            "deletedRecords": deleted_counts
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
