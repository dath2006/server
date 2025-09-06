from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from app.database import get_db
from app.crud.permissions import (
    get_group_by_name, 
    get_group_by_id,
    get_all_groups,
    get_permissions_by_group_name,
    get_permissions_by_group_id,
    map_role_to_permissions
)
from app.schemas import PermissionsForRoleResponse, AvailableRolesResponse, GroupResponse

router = APIRouter(prefix="/permissions", tags=["permissions"])

# Standard role to group ID mapping - Fixed to match actual database schema
STANDARD_ROLES = {
    "admin": 1,    # Admin group
    "member": 2,   # Member group (default for new users)
    "friend": 3,   # Friend group
    "banned": 4,   # Banned group
    "guest": 5,    # Guest group (unauthenticated users)
    "editor": 2,   # Map editor to member group for backward compatibility
    "contributor": 3,  # Map contributor to friend group for backward compatibility
}


@router.get("/", response_model=PermissionsForRoleResponse)
@router.get("", response_model=PermissionsForRoleResponse)  # Handle both with and without trailing slash
async def get_permissions_for_role(
    role: str = Query(..., description="Role name: guest, member, friend, banned, admin, editor, or custom group name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all permissions for a specific role/group.
    
    Parameters:
    - role: Can be a standard role (guest, member, friend, banned, admin, editor) or a custom group name
    
    Returns all ultimate permissions with true/false values based on what exists in the database.
    """
    
    role_lower = role.lower()
    group = None
    group_id = None
    
    # Check if it's a standard role
    if role_lower in STANDARD_ROLES:
        group_id = STANDARD_ROLES[role_lower]
        group = await get_group_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=404, 
                detail=f"Standard role '{role}' group not found in database"
            )
    else:
        # Try to find custom group by name
        group = await get_group_by_name(db, role)
        if not group:
            raise HTTPException(
                status_code=404,
                detail=f"Role/Group '{role}' not found"
            )
        group_id = group.id
    
    # Get permissions for the group
    permissions_from_db = await get_permissions_by_group_id(db, group_id)
    
    # Map to ultimate permissions list
    permissions_dict = map_role_to_permissions(permissions_from_db)
    
    return PermissionsForRoleResponse(
        role=role,
        group_id=group_id,
        group_name=group.name,
        permissions=permissions_dict
    )


@router.get("/roles", response_model=AvailableRolesResponse)
async def get_available_roles(db: AsyncSession = Depends(get_db)):
    """
    Get all available roles/groups in the system.
    
    Returns both standard role names and all groups from the database.
    """
    
    # Get all groups from database
    groups = await get_all_groups(db)
    
    # Standard roles list
    standard_roles = list(STANDARD_ROLES.keys())
    
    # Convert groups to response format
    group_responses = [
        GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at
        )
        for group in groups
    ]
    
    return AvailableRolesResponse(
        roles=standard_roles,
        groups=group_responses
    )
