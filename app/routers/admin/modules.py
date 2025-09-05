from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.crud import modules as modules_crud
from app.schemas import ModulesResponse, ModuleResponse, ModuleUpdate
from app.auth import get_current_active_user, require_admin_permission
from app.models import User

router = APIRouter()

@router.get("/modules", response_model=ModulesResponse)
async def get_all_modules(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all modules.
    Requires admin permissions.
    """
    require_admin_permission(current_user)
    
    modules = await modules_crud.get_modules(db)
    return ModulesResponse(
        data=[ModuleResponse.model_validate(module) for module in modules],
        total=len(modules)
    )

@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module_status(
    module_id: int,
    module_update: ModuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update module status.
    Requires admin permissions.
    """
    require_admin_permission(current_user)
    
    module = await modules_crud.update_module(db, module_id, module_update)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    return ModuleResponse.model_validate(module)

@router.delete("/modules/{module_id}")
async def uninstall_module(
    module_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uninstall a module.
    Requires admin permissions.
    """
    require_admin_permission(current_user)
    
    # Check if module exists and can be uninstalled
    module = await modules_crud.get_module_by_id(db, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    if module.canUninstall is False:
        raise HTTPException(status_code=400, detail="Module cannot be uninstalled")
    
    success = await modules_crud.delete_module(db, module_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to uninstall module")
    
    return {"message": "Module uninstalled successfully", "module_id": module_id}
