from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models import Module
from app.schemas import ModuleUpdate

async def get_modules(db: AsyncSession) -> List[Module]:
    """Get all modules"""
    result = await db.execute(select(Module).order_by(Module.name))
    return result.scalars().all()

async def get_module_by_id(db: AsyncSession, module_id: int) -> Optional[Module]:
    """Get a module by ID"""
    result = await db.execute(select(Module).where(Module.id == module_id))
    return result.scalars().first()

async def update_module(db: AsyncSession, module_id: int, module_update: ModuleUpdate) -> Optional[Module]:
    """Update a module"""
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalars().first()
    
    if not module:
        return None
    
    if module_update.status is not None:
        module.status = module_update.status
    
    await db.commit()
    await db.refresh(module)
    return module

async def delete_module(db: AsyncSession, module_id: int) -> bool:
    """Delete a module"""
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalars().first()
    
    if not module:
        return False
    
    # Check if module can be uninstalled
    if module.canUninstall is False:
        return False
    
    await db.delete(module)
    await db.commit()
    return True
