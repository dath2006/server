from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.crud import themes as themes_crud
from app.schemas import ThemesResponse, ThemeResponse
from app.auth import get_current_active_user, require_admin_permission
from app.models import User

router = APIRouter()

@router.get("/themes", response_model=ThemesResponse)
async def get_all_themes(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all themes.
    Requires admin permissions.
    """
    require_admin_permission(current_user)
    
    themes = await themes_crud.get_themes(db)
    return ThemesResponse(
        data=[ThemeResponse.model_validate(theme) for theme in themes],
        total=len(themes)
    )

@router.put("/themes/{theme_id}/activate", response_model=ThemeResponse)
async def activate_theme(
    theme_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate a theme (deactivates all other themes).
    Requires admin permissions.
    """
    require_admin_permission(current_user)
    
    theme = await themes_crud.activate_theme(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    return ThemeResponse.model_validate(theme)
