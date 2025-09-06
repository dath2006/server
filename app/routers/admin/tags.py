from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, delete, distinct
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Tag, Post, PostAttribute

router = APIRouter()


@router.get("/tags", response_model=Dict[str, Any])
async def get_admin_tags(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of tags per page"),
    search: Optional[str] = Query(None, description="Search in tag name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tags for admin panel with pagination and filtering"""
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Get unique tags with post counts
    # Since tags can be duplicated across different posts, we need to group by name
    unique_tags_query = select(
        Tag.name,
        func.min(Tag.id).label('id'),
        func.min(Tag.created_at).label('created_at'),
        func.min(Tag.status).label('status'),
        func.count(distinct(Tag.post_id)).label('post_count')
    ).group_by(Tag.name)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        unique_tags_query = unique_tags_query.where(Tag.name.ilike(search_term))
    
    # Get total count for pagination
    count_subquery = unique_tags_query.subquery()
    total_result = await db.execute(select(func.count()).select_from(count_subquery))
    total_tags = total_result.scalar()
    
    # Apply pagination and ordering
    unique_tags_query = unique_tags_query.order_by(desc(func.count(distinct(Tag.post_id)))).offset(offset).limit(limit)
    
    result = await db.execute(unique_tags_query)
    tag_data = result.all()
    
    # Process tags into required format
    tags_data = []
    for tag in tag_data:
        tag_info = {
            "id": str(tag.id),
            "name": tag.name,
            "createdAt": tag.created_at.isoformat() if tag.created_at else None,
            "postCount": tag.post_count,
            "status": tag.status or "published"
        }
        tags_data.append(tag_info)
    
    # Calculate pagination metadata
    total_pages = (total_tags + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        "data": tags_data,
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalTags": total_tags,
            "limit": limit,
            "hasNext": has_next,
            "hasPrevious": has_previous,
            "nextPage": page + 1 if has_next else None,
            "previousPage": page - 1 if has_previous else None
        },
        "filters": {
            "search": search
        }
    }


@router.get("/tags/{tag_id}", response_model=Dict[str, Any])
async def get_admin_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single tag with associated posts"""
    
    # Get the tag first
    tag_result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Get all posts that have this tag name (since tags can be duplicated across posts)
    posts_query = select(Post).options(
        selectinload(Post.user),
        selectinload(Post.attributes),
        selectinload(Post.tags)
    ).join(Tag).where(Tag.name == tag.name)
    
    posts_result = await db.execute(posts_query)
    posts = posts_result.scalars().all()
    
    # Process posts into required format
    posts_data = []
    for post in posts:
        post_data = {
            "id": str(post.id),
            "title": post.title,
            "author": {
                "name": post.user.full_name if post.user and post.user.full_name else (post.user.username if post.user else "Unknown"),
                "avatar": post.user.image if post.user else None
            },
            "createdAt": post.attributes.created_at.isoformat() if post.attributes and post.attributes.created_at else None,
            "tags": [t.name for t in post.tags] if post.tags else [],
            "status": post.attributes.status if post.attributes else "draft"
        }
        posts_data.append(post_data)
    
    # Get post count for this tag name
    post_count = len(posts)
    
    tag_data = {
        "id": str(tag.id),
        "name": tag.name,
        "createdAt": tag.created_at.isoformat() if tag.created_at else None,
        "postCount": post_count,
        "status": tag.status or "published",
        "posts": posts_data
    }
    
    return tag_data


@router.post("/tags", response_model=Dict[str, Any])
async def create_admin_tag(
    tag_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new tag by linking it to existing post(s)"""
    
    # Validate required fields
    if not tag_data.get("name"):
        raise HTTPException(status_code=400, detail="Tag name is required")
    
    tag_name = tag_data["name"].strip()
    
    if not tag_name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")
    
    # Handle both old format (single post_id) and new format (selectedPostIds)
    post_ids = []
    
    if tag_data.get("selectedPostIds"):
        # New format: multiple posts
        for post_id_str in tag_data["selectedPostIds"]:
            try:
                # Convert post_id from string format "post_X" to integer X
                if post_id_str.startswith("post_"):
                    post_id = int(post_id_str.replace("post_", ""))
                else:
                    post_id = int(post_id_str)
                post_ids.append(post_id)
            except (ValueError, TypeError):
                continue  # Skip invalid post IDs
    elif tag_data.get("post_id"):
        # Old format: single post
        post_ids = [tag_data["post_id"]]
    
    if not post_ids:
        raise HTTPException(status_code=400, detail="At least one post ID is required to create a tag")
    
    try:
        attached_posts = []
        skipped_posts = []
        created_tags = []
        
        for post_id in post_ids:
            # Check if post exists
            post_result = await db.execute(
                select(Post).where(Post.id == post_id)
            )
            post = post_result.scalar_one_or_none()
            
            if not post:
                skipped_posts.append({
                    "id": str(post_id),
                    "reason": "Post not found"
                })
                continue
            
            # Check if tag already exists for this post
            existing_tag = await db.execute(
                select(Tag).where(Tag.post_id == post_id, Tag.name == tag_name)
            )
            if existing_tag.scalar_one_or_none():
                skipped_posts.append({
                    "id": str(post_id),
                    "title": post.title,
                    "reason": "Tag already exists for this post"
                })
                continue
            
            # Create tag linked to the post
            tag = Tag(
                name=tag_name,
                post_id=post_id,
                user_id=current_user.id,
                status=tag_data.get("status", "published")
            )
            
            db.add(tag)
            created_tags.append(tag)
            attached_posts.append({
                "id": str(post_id),
                "title": post.title
            })
        
        if not created_tags:
            raise HTTPException(status_code=400, detail="No tags were created. All posts either don't exist or already have this tag.")
        
        await db.commit()
        
        # Get post count for this tag name
        post_count_result = await db.execute(
            select(func.count(distinct(Tag.post_id))).where(Tag.name == tag_name)
        )
        post_count = post_count_result.scalar()
        
        # Use the first created tag for the main response
        first_tag = created_tags[0]
        
        response_data = {
            "id": str(first_tag.id),
            "name": first_tag.name,
            "createdAt": first_tag.created_at.isoformat() if first_tag.created_at else None,
            "postCount": post_count,
            "status": first_tag.status or "published",
            "message": f"Tag created successfully for {len(attached_posts)} post(s)"
        }
        
        # Add processing results
        response_data["processing"] = {
            "attachedPosts": attached_posts,
            "skippedPosts": skipped_posts,
            "totalAttached": len(attached_posts),
            "totalSkipped": len(skipped_posts),
            "createdTags": len(created_tags)
        }
        
        # For backward compatibility, include linkedPost if only one post was processed
        if len(attached_posts) == 1:
            response_data["linkedPost"] = attached_posts[0]
        
        return response_data
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error creating tag: {str(e)}")


@router.put("/tags/{tag_id}", response_model=Dict[str, Any])
async def update_admin_tag(
    tag_id: int,
    tag_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a tag (updates all instances of the tag across all posts)"""
    
    # Get the tag first
    tag_result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    try:
        old_name = tag.name
        new_name = old_name  # Default to current name
        
        # Update tag name if provided
        if "name" in tag_data and tag_data["name"]:
            new_name = tag_data["name"].strip()
            
            if new_name != old_name:
                # Check if new name already exists
                existing_tag = await db.execute(
                    select(Tag).where(Tag.name == new_name).limit(1)
                )
                if existing_tag.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Tag with this name already exists")
                
                # Update all tags with the old name to the new name
                await db.execute(
                    Tag.__table__.update().where(Tag.name == old_name).values(name=new_name)
                )
        
        # Update status if provided
        if "status" in tag_data:
            status_value = tag_data["status"]
            if status_value in ["published", "draft", "archived"]:
                # Update all tags with this name to the new status
                await db.execute(
                    Tag.__table__.update().where(Tag.name == old_name).values(status=status_value)
                )
        
        # Handle selectedPostIds if provided
        attached_posts = []
        skipped_posts = []
        
        if "selectedPostIds" in tag_data and tag_data["selectedPostIds"]:
            selected_post_ids = tag_data["selectedPostIds"]
            
            for post_id_str in selected_post_ids:
                try:
                    # Convert post_id from string format "post_X" to integer X
                    if post_id_str.startswith("post_"):
                        post_id = int(post_id_str.replace("post_", ""))
                    else:
                        post_id = int(post_id_str)
                    
                    # Check if post exists
                    post_result = await db.execute(
                        select(Post).where(Post.id == post_id)
                    )
                    post = post_result.scalar_one_or_none()
                    
                    if not post:
                        continue  # Skip non-existent posts
                    
                    # Check if tag already exists for this post
                    existing_tag_result = await db.execute(
                        select(Tag).where(Tag.post_id == post_id, Tag.name == new_name)
                    )
                    existing_tag_for_post = existing_tag_result.scalar_one_or_none()
                    
                    if existing_tag_for_post:
                        # Tag already exists for this post, skip it
                        skipped_posts.append({
                            "id": str(post_id),
                            "title": post.title,
                            "reason": "Tag already attached"
                        })
                    else:
                        # Create new tag for this post
                        new_tag = Tag(
                            name=new_name,
                            post_id=post_id,
                            user_id=current_user.id,
                            status=tag_data.get("status", "published")
                        )
                        db.add(new_tag)
                        attached_posts.append({
                            "id": str(post_id),
                            "title": post.title
                        })
                
                except (ValueError, TypeError):
                    # Skip invalid post IDs
                    continue
        
        await db.commit()
        
        # Get updated tag info
        updated_tag_result = await db.execute(
            select(Tag).where(Tag.id == tag_id)
        )
        updated_tag = updated_tag_result.scalar_one()
        
        # Get post count for this tag
        post_count_result = await db.execute(
            select(func.count(distinct(Tag.post_id))).where(Tag.name == updated_tag.name)
        )
        post_count = post_count_result.scalar()
        
        response_data = {
            "id": str(updated_tag.id),
            "name": updated_tag.name,
            "createdAt": updated_tag.created_at.isoformat() if updated_tag.created_at else None,
            "postCount": post_count,
            "status": updated_tag.status or "published",
            "message": "Tag updated successfully"
        }
        
        # Add selectedPostIds processing results if any were provided
        if "selectedPostIds" in tag_data:
            response_data["selectedPostsProcessing"] = {
                "attachedPosts": attached_posts,
                "skippedPosts": skipped_posts,
                "totalAttached": len(attached_posts),
                "totalSkipped": len(skipped_posts)
            }
        
        return response_data
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error updating tag: {str(e)}")


@router.delete("/tags/{tag_id}", response_model=Dict[str, Any])
async def delete_admin_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a tag (removes all instances of the tag across all posts)"""
    
    # Get the tag first
    tag_result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    try:
        tag_name = tag.name
        
        # Count how many posts will be affected
        affected_posts_result = await db.execute(
            select(func.count(distinct(Tag.post_id))).where(Tag.name == tag_name)
        )
        affected_posts_count = affected_posts_result.scalar()
        
        # Count total tag instances
        total_instances_result = await db.execute(
            select(func.count(Tag.id)).where(Tag.name == tag_name)
        )
        total_instances = total_instances_result.scalar()
        
        # Delete all instances of this tag
        await db.execute(
            delete(Tag).where(Tag.name == tag_name)
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Tag '{tag_name}' deleted successfully",
            "deletedTag": {
                "id": str(tag.id),
                "name": tag_name,
                "status": tag.status or "published"
            },
            "affectedPosts": affected_posts_count,
            "deletedInstances": total_instances
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting tag: {str(e)}")


@router.get("/tags/stats", response_model=Dict[str, Any])
async def get_tags_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tags statistics for admin dashboard"""
    
    # Total unique tags
    unique_tags_result = await db.execute(
        select(func.count(distinct(Tag.name)))
    )
    total_unique_tags = unique_tags_result.scalar()
    
    # Total tag instances
    total_instances_result = await db.execute(
        select(func.count(Tag.id))
    )
    total_instances = total_instances_result.scalar()
    
    # Tags by status
    status_query = select(
        Tag.status,
        func.count(distinct(Tag.name)).label('count')
    ).group_by(Tag.status)
    
    status_result = await db.execute(status_query)
    tags_by_status = {row.status or "published": row.count for row in status_result}
    
    # Most used tags (top 10)
    popular_tags_query = select(
        Tag.name,
        func.count(distinct(Tag.post_id)).label('post_count')
    ).group_by(Tag.name).order_by(desc(func.count(distinct(Tag.post_id)))).limit(10)
    
    popular_result = await db.execute(popular_tags_query)
    popular_tags = [
        {"name": row.name, "postCount": row.post_count}
        for row in popular_result
    ]
    
    # Recent tags (created in last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_tags_result = await db.execute(
        select(func.count(distinct(Tag.name)))
        .where(Tag.created_at >= thirty_days_ago)
    )
    recent_tags = recent_tags_result.scalar()
    
    return {
        "totalUniqueTags": total_unique_tags,
        "totalInstances": total_instances,
        "tagsByStatus": tags_by_status,
        "popularTags": popular_tags,
        "recentTags": recent_tags,
        "generatedAt": datetime.utcnow().isoformat()
    }
