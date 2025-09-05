
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.crud import settings as settings_crud
from app.schemas import (
    SettingResponse, 
    UpdateSettingData, 
    UpdateSettingsData,
    AdminSettingsResponse,
    UpdateSettingsResponse,
    SingleSettingResponse
)
from app.auth import get_current_active_user, require_admin_permission
from app.models import User

router = APIRouter()


@router.get("/settings", response_model=AdminSettingsResponse)
async def get_all_settings(
    group: Optional[str] = Query(None, description="Filter settings by group/category"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all settings.
    Optionally filter by group parameter (for future categorization).
    """
    require_admin_permission(current_user)
    try:
        settings = await settings_crud.get_settings(db)
        return AdminSettingsResponse(
            success=True,
            data=settings,
            message=f"Retrieved {len(settings)} settings successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve settings: {str(e)}")


@router.get("/settings/{name}", response_model=SingleSettingResponse)
async def get_setting_by_name(
    name: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific setting by name.
    """
    require_admin_permission(current_user)
    setting = await settings_crud.get_setting_by_name(db, name)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{name}' not found")
    return SingleSettingResponse(
        success=True,
        data=setting,
        message=f"Setting '{name}' retrieved successfully"
    )


@router.put("/settings", response_model=UpdateSettingsResponse)
async def update_multiple_settings(
    settings_data: UpdateSettingsData,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update multiple settings at once.
    """
    require_admin_permission(current_user)
    try:
        settings_dict = {}
        for name, data in settings_data.settings.items():
            settings_dict[name] = {
                "value": data.value,
                "type": data.type,
                "description": data.description
            }
        updated_settings = await settings_crud.update_multiple_settings(db, settings_dict)
        return UpdateSettingsResponse(
            success=True,
            data=updated_settings,
            message=f"Successfully updated {len(updated_settings)} settings"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.put("/settings/{name}", response_model=SingleSettingResponse)
async def update_single_setting(
    name: str,
    setting_data: UpdateSettingData,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a single setting by name.
    Creates the setting if it doesn't exist.
    """
    require_admin_permission(current_user)
    try:
        updated_setting = await settings_crud.update_setting_by_name(
            db, 
            name, 
            setting_data.value,
            setting_data.type,
            setting_data.description
        )
        if not updated_setting:
            raise HTTPException(status_code=500, detail=f"Failed to update setting '{name}'")
        return SingleSettingResponse(
            success=True,
            data=updated_setting,
            message=f"Setting '{name}' updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting '{name}': {str(e)}")


@router.delete("/settings/{name}")
async def delete_setting(
    name: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a setting by name.
    """
    require_admin_permission(current_user)
    setting = await settings_crud.get_setting_by_name(db, name)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{name}' not found")
    success = await settings_crud.delete_setting(db, setting)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete setting '{name}'")
    return {
        "success": True,
        "message": f"Setting '{name}' deleted successfully"
    }
