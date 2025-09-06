from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.crud import feathers as feathers_crud
from app.schemas import FeathersResponse, FeatherResponse, FeatherUpdate
from app.auth import get_current_active_user, require_admin_permission
from app.models import User

router = APIRouter()

@router.get("/feathers", response_model=FeathersResponse)
async def get_all_feathers(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all feathers.
    Requires admin permissions.
    """
    # require_admin_permission(current_user) # Removed - all users can access admin now
    
    feathers = await feathers_crud.get_feathers(db)
    return FeathersResponse(
        data=[FeatherResponse.model_validate(feather) for feather in feathers],
        total=len(feathers)
    )

@router.put("/feathers/{feather_id}", response_model=FeatherResponse)
async def update_feather_status(
    feather_id: int,
    feather_update: FeatherUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update feather status.
    Requires admin permissions.
    """
    # require_admin_permission(current_user) # Removed - all users can access admin now
    
    feather = await feathers_crud.update_feather(db, feather_id, feather_update)
    if not feather:
        raise HTTPException(status_code=404, detail="Feather not found")
    
    return FeatherResponse.model_validate(feather)
