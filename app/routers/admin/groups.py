from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Group, Permission

router = APIRouter()


@router.get("/groups", response_model=Dict[str, Any])
async def get_admin_groups(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of groups per page"),
    search: Optional[str] = Query(None, description="Search in group name or description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get groups for admin panel with pagination and filtering"""
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Base query with comprehensive relationship loading
    query = select(Group).options(
        selectinload(Group.users),
        selectinload(Group.permissions)
    )
    
    # Apply filters
    conditions = []
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        conditions.append(
            (Group.name.ilike(search_term)) | 
            (Group.description.ilike(search_term))
        )
    
    # Apply all conditions
    if conditions:
        for condition in conditions:
            query = query.where(condition)
    
    # Get total count for pagination
    count_query = select(func.count(Group.id))
    if conditions:
        for condition in conditions:
            count_query = count_query.where(condition)
    
    total_result = await db.execute(count_query)
    total_groups = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(Group.id)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    groups = result.scalars().all()
    
    # Process groups into required format
    groups_data = []
    for group in groups:
        # Calculate user count
        user_count = len(group.users) if group.users else 0
        
        # Get permission names
        permission_names = [permission.name for permission in group.permissions] if group.permissions else []
        
        group_data = {
            "id": str(group.id),
            "name": group.name,
            "userCount": user_count,
            "createdAt": group.created_at.isoformat() if group.created_at else None,
            "description": group.description,
            "permissions": permission_names
        }
        
        groups_data.append(group_data)
    
    # Calculate pagination metadata
    total_pages = (total_groups + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        "data": groups_data,
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalGroups": total_groups,
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


@router.get("/groups/{group_id}", response_model=Dict[str, Any])
async def get_admin_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single group for admin panel"""
    query = select(Group).options(
        selectinload(Group.users),
        selectinload(Group.permissions)
    ).where(Group.id == group_id)
    
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    # Calculate user count
    user_count = len(group.users) if group.users else 0
    
    # Get permission names
    permission_names = [permission.name for permission in group.permissions] if group.permissions else []

    group_data = {
        "id": str(group.id),
        "name": group.name,
        "userCount": user_count,
        "createdAt": group.created_at.isoformat() if group.created_at else None,
        "description": group.description,
        "permissions": permission_names,
        "users": [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "fullName": user.full_name,
                "isActive": user.is_active
            }
            for user in group.users
        ] if group.users else []
    }
    
    return group_data


@router.post("/groups", response_model=Dict[str, Any])
async def create_admin_group(
    group_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new group"""
    
    # Validate required fields
    if not group_data.get("name"):
        raise HTTPException(status_code=400, detail="Group name is required")
    
    # Check if group name already exists
    existing_group = await db.execute(
        select(Group).where(Group.name == group_data["name"])
    )
    if existing_group.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    try:
        # Create group record
        group = Group(
            name=group_data["name"],
            description=group_data.get("description")
        )
        
        db.add(group)
        await db.flush()  # Get group ID
        
        # Add permissions if provided
        if group_data.get("permissions"):
            for permission_name in group_data["permissions"]:
                if permission_name.strip():
                    permission = Permission(
                        group_id=group.id,
                        name=permission_name.strip(),
                        description=f"Permission: {permission_name.strip()}"
                    )
                    db.add(permission)
        
        await db.commit()
        
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "userCount": 0,
            "permissions": group_data.get("permissions", []),
            "createdAt": group.created_at.isoformat(),
            "message": "Group created successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")


@router.put("/groups/{group_id}", response_model=Dict[str, Any])
async def update_admin_group(
    group_id: int,
    group_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing group"""
    
    # Check if group exists
    result = await db.execute(
        select(Group).options(
            selectinload(Group.permissions),
            selectinload(Group.users)
        ).where(Group.id == group_id)
    )
    existing_group = result.scalar_one_or_none()
    
    if not existing_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Prevent modification of system groups (you might want to add this logic)
    # For now, we'll allow all modifications
    
    try:
        # Check if group name is being changed and already exists
        if "name" in group_data and group_data["name"] != existing_group.name:
            existing_name = await db.execute(
                select(Group).where(Group.name == group_data["name"])
            )
            if existing_name.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Group name already exists")
            existing_group.name = group_data["name"]
        
        # Update description
        if "description" in group_data:
            existing_group.description = group_data["description"]
        
        # Handle permissions update
        if "permissions" in group_data:
            # Remove existing permissions
            await db.execute(
                delete(Permission).where(Permission.group_id == group_id)
            )
            
            # Flush to ensure deletion is committed before adding new permissions
            await db.flush()
            
            # Add new permissions
            if group_data["permissions"]:
                for permission_name in group_data["permissions"]:
                    if permission_name.strip():
                        permission = Permission(
                            group_id=group_id,
                            name=permission_name.strip(),
                            description=f"Permission: {permission_name.strip()}"
                        )
                        db.add(permission)
        
        await db.commit()
        
        # Reload group with relationships
        updated_result = await db.execute(
            select(Group).options(
                selectinload(Group.permissions),
                selectinload(Group.users)
            ).where(Group.id == group_id)
        )
        updated_group = updated_result.scalar_one()
        
        # Calculate user count
        user_count = len(updated_group.users) if updated_group.users else 0
        
        # Get permission names
        permission_names = [permission.name for permission in updated_group.permissions] if updated_group.permissions else []
        
        return {
            "id": str(updated_group.id),
            "name": updated_group.name,
            "description": updated_group.description,
            "userCount": user_count,
            "permissions": permission_names,
            "createdAt": updated_group.created_at.isoformat() if updated_group.created_at else None,
            "message": "Group updated successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error updating group: {str(e)}")


@router.delete("/groups/{group_id}", response_model=Dict[str, Any])
async def delete_admin_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a group and handle associated data"""
    
    # Check if group exists
    result = await db.execute(
        select(Group).options(
            selectinload(Group.permissions),
            selectinload(Group.users)
        ).where(Group.id == group_id)
    )
    existing_group = result.scalar_one_or_none()
    
    if not existing_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Prevent deletion of system groups
    system_groups = [1, 2, 3, 4, 5]  # Admin, Editor, Contributor, Member, Default member
    if group_id in system_groups:
        raise HTTPException(status_code=400, detail="Cannot delete system groups")
    
    # Check if group has users
    if existing_group.users and len(existing_group.users) > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete group with {len(existing_group.users)} users. Please reassign users first."
        )
    
    try:
        deleted_counts = {
            "permissions": 0,
            "users": 0
        }
        
        # Count items before deletion
        if existing_group.permissions:
            deleted_counts["permissions"] = len(existing_group.permissions)
        if existing_group.users:
            deleted_counts["users"] = len(existing_group.users)
        
        # Delete associated permissions
        if existing_group.permissions:
            await db.execute(delete(Permission).where(Permission.group_id == group_id))
        
        # Note: We don't delete users, we just check they don't exist above
        # In a real scenario, you might want to reassign users to a default group
        
        # Finally, delete the group itself
        await db.execute(delete(Group).where(Group.id == group_id))
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Group deleted successfully",
            "deletedGroup": {
                "id": str(existing_group.id),
                "name": existing_group.name,
                "description": existing_group.description
            },
            "deletedRecords": deleted_counts
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting group: {str(e)}")
