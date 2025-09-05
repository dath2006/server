from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.crud import settings as settings_crud
from app.crud.modules import get_modules
from app.crud.themes import get_themes
from app.crud.feathers import get_feathers

router = APIRouter()
security = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    try:
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        # Import here to avoid circular imports
        from app.auth import get_current_user
        
        # Create a mock security dependency result
        from fastapi.security.http import HTTPAuthorizationCredentials
        
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            
            # Use the existing get_current_user function
            import jwt
            from jwt import PyJWTError
            from app.config import settings as app_settings
            from sqlalchemy import select
            
            try:
                payload = jwt.decode(token, app_settings.SECRET_KEY, algorithms=["HS256"])
                email: str = payload.get("email")
                user_id: int = payload.get("user_id")
                
                if email is None or user_id is None:
                    return None
                    
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalars().first()
                return user if user and user.approved else None
                
            except PyJWTError:
                return None
        
        return None
    except Exception:
        return None

def parse_setting_value(value: str, setting_type: str) -> Any:
    """Parse setting value based on its type"""
    if setting_type == "boolean":
        return value.lower() in ("true", "1", "yes", "on")
    elif setting_type == "number":
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return 0
    elif setting_type == "json":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    else:
        return value

@router.get("/settings")
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get site settings - returns data based on authentication status
    
    - Public settings are returned for all users
    - Sensitive settings are only returned for authenticated admin users
    """
    try:
        # Get current user if authenticated (optional)
        current_user = await get_current_user_optional(request, db)
        # Get all data from the database
        settings = await settings_crud.get_settings(db)
        modules = await get_modules(db)
        themes = await get_themes(db)
        feathers = await get_feathers(db)
        
        # Convert settings to dictionary with proper type conversion
        settings_dict = {}
        for setting in settings:
            settings_dict[setting.name] = parse_setting_value(setting.value, setting.type)
        
        # Get user role for permission checking
        user_role = None
        if current_user:
            from app.auth import get_user_role
            user_role = get_user_role(current_user.group_id)
        
        # Define sensitive settings that require admin access
        sensitive_settings = {
            'admin_email', 'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_encryption', 'database_url', 'secret_key', 'jwt_secret',
            'google_client_id', 'google_client_secret', 'api_keys'
        }
        
        # Filter sensitive settings if user is not admin
        if user_role != "admin":
            # Remove sensitive settings for non-admin users
            for sensitive in sensitive_settings:
                settings_dict.pop(sensitive, None)
        
        # Build the response with all the data
        response_data = {
            # Basic site settings with fallbacks
            "site_title": settings_dict.get("site_title", "Chyrp Lite"),
            "site_description": settings_dict.get("site_description", ""),
            "site_url": settings_dict.get("site_url", ""),
            "timezone": settings_dict.get("timezone", "UTC"),
            "locale": settings_dict.get("locale", "en"),
            
            # Content settings
            "posts_per_page": settings_dict.get("posts_per_page", 10),
            "enable_registration": settings_dict.get("enable_registration", True),
            "enable_comments": settings_dict.get("enable_comments", True),
            "enable_trackbacks": settings_dict.get("enable_trackbacks", False),
            "enable_webmentions": settings_dict.get("enable_webmentions", False),
            "enable_feeds": settings_dict.get("enable_feeds", True),
            "enable_search": settings_dict.get("enable_search", True),
            "maintenance_mode": settings_dict.get("maintenance_mode", False),
            
            # Get current active theme
            "theme": next((theme.name for theme in themes if theme.isActive), "default"),
            
            # Social links (parse from JSON if exists)
            "social_links": settings_dict.get("social_links", {}),
            
            # SEO settings (parse from JSON if exists)
            "seo_settings": settings_dict.get("seo_settings", {}),
            
            # Email settings (only for admin users)
            **({"admin_email": settings_dict.get("admin_email", "")} if user_role == "admin" else {}),
            **({"smtp_settings": {
                "host": settings_dict.get("smtp_host", ""),
                "port": settings_dict.get("smtp_port", 587),
                "username": settings_dict.get("smtp_username", ""),
                "password": settings_dict.get("smtp_password", ""),
                "encryption": settings_dict.get("smtp_encryption", "tls")
            }} if user_role == "admin" else {}),
            
            # Module information
            "modules": [
                {
                    "id": module.id,
                    "name": module.name,
                    "description": module.description,
                    "status": module.status,
                    "can_disable": module.canDisable,
                    "can_uninstall": module.canUninstall,
                    "conflicts": module.conflicts
                }
                for module in modules
            ],
            
            # Theme information
            "themes": [
                {
                    "id": theme.id,
                    "name": theme.name,
                    "description": theme.description,
                    "is_active": theme.isActive or False
                }
                for theme in themes
            ],
            
            # Feather information
            "feathers": [
                {
                    "id": feather.id,
                    "name": feather.name,
                    "description": feather.description,
                    "status": feather.status,
                    "can_disable": feather.canDisable
                }
                for feather in feathers
            ],
            
            # Add any other settings that don't have specific handling
            **{k: v for k, v in settings_dict.items() 
               if k not in {
                   'site_title', 'site_description', 'site_url', 'timezone', 'locale',
                   'posts_per_page', 'enable_registration', 'enable_comments', 
                   'enable_trackbacks', 'enable_webmentions', 'enable_feeds', 
                   'enable_search', 'maintenance_mode', 'admin_email',
                   'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_encryption',
                   'social_links', 'seo_settings'
               } and (user_role == "admin" or k not in sensitive_settings)}
        }
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching settings: {str(e)}")


@router.put("/settings")
async def update_settings(
    settings_update: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Update site settings (Admin only)
    
    Accepts a dictionary of settings to update and creates/updates them in the database
    """
    try:
        # Get current user (required for updates)
        current_user = await get_current_user_optional(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Check if user is admin
        from app.auth import get_user_role
        user_role = get_user_role(current_user.group_id)
        if user_role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Update settings
        updated_settings = []
        for key, value in settings_update.items():
            # Skip nested objects for now - handle them separately if needed
            if isinstance(value, dict):
                # Convert dict to JSON string
                value_str = json.dumps(value)
                setting_type = "json"
            elif isinstance(value, bool):
                value_str = str(value).lower()
                setting_type = "boolean"
            elif isinstance(value, (int, float)):
                value_str = str(value)
                setting_type = "number"
            else:
                value_str = str(value)
                setting_type = "string"
            
            setting = await settings_crud.update_setting_by_name(
                db, key, value_str, setting_type
            )
            if setting:
                updated_settings.append(setting)
        
        # Return the updated settings in the same format as GET
        return await get_settings(request, db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")
