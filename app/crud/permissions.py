from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Optional
from app.models import Group, Permission


async def get_group_by_name(db: AsyncSession, group_name: str) -> Optional[Group]:
    """Get group by name"""
    result = await db.execute(select(Group).filter(Group.name.ilike(group_name)))
    return result.scalars().first()


async def get_group_by_id(db: AsyncSession, group_id: int) -> Optional[Group]:
    """Get group by ID"""
    result = await db.execute(select(Group).filter(Group.id == group_id))
    return result.scalars().first()


async def get_all_groups(db: AsyncSession) -> List[Group]:
    """Get all groups"""
    result = await db.execute(select(Group))
    return result.scalars().all()


async def get_permissions_by_group_id(db: AsyncSession, group_id: int) -> List[Permission]:
    """Get all permissions for a specific group"""
    result = await db.execute(select(Permission).filter(Permission.group_id == group_id))
    return result.scalars().all()


async def get_permissions_by_group_name(db: AsyncSession, group_name: str) -> List[Permission]:
    """Get all permissions for a group by group name"""
    # First get the group
    group = await get_group_by_name(db, group_name)
    if not group:
        return []
    
    # Then get permissions for that group
    return await get_permissions_by_group_id(db, group.id)


def get_ultimate_permissions_list() -> List[str]:
    """Return the ultimate permissions list as defined in the requirements"""
    return [
        "add_comments",
        "add_comments_private", 
        "add_drafts",
        "add_groups",
        "add_pages",
        "add_posts",
        "add_uploads",
        "add_users",
        "change_settings",
        "use_html_comments",
        "delete_comments",
        "delete_drafts",
        "delete_groups",
        "delete_own_comments",
        "delete_own_drafts",
        "delete_own_posts",
        "delete_pages",
        "delete_webmentions",
        "delete_posts",
        "delete_uploads",
        "delete_users",
        "edit_comments",
        "edit_drafts",
        "edit_groups",
        "edit_own_comments",
        "edit_own_drafts",
        "edit_own_posts",
        "edit_pages",
        "edit_webmentions",
        "edit_posts",
        "edit_uploads",
        "edit_users",
        "export_content",
        "import_content",
        "like_posts",
        "manage_categories",
        "toggle_extensions",
        "unlike_posts",
        "view_drafts",
        "view_own_drafts",
        "view_pages",
        "view_private_posts",
        "view_scheduled_posts",
        "view_site",
        "view_uploads"
    ]


def map_role_to_permissions(permissions_from_db: List[Permission]) -> Dict[str, bool]:
    """Map database permissions to ultimate permissions list"""
    ultimate_permissions = get_ultimate_permissions_list()
    permissions_dict = {perm: False for perm in ultimate_permissions}
    
    # Get permission names from database
    db_permission_names = [perm.name for perm in permissions_from_db]
    
    # Set to True for permissions that exist in database
    for perm_name in db_permission_names:
        if perm_name in permissions_dict:
            permissions_dict[perm_name] = True
    
    return permissions_dict
