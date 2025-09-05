from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models import Feather
from app.schemas import FeatherUpdate

async def get_feathers(db: AsyncSession) -> List[Feather]:
    """Get all feathers"""
    result = await db.execute(select(Feather).order_by(Feather.name))
    return result.scalars().all()

async def get_feather_by_id(db: AsyncSession, feather_id: int) -> Optional[Feather]:
    """Get a feather by ID"""
    result = await db.execute(select(Feather).where(Feather.id == feather_id))
    return result.scalars().first()

async def update_feather(db: AsyncSession, feather_id: int, feather_update: FeatherUpdate) -> Optional[Feather]:
    """Update a feather"""
    result = await db.execute(select(Feather).where(Feather.id == feather_id))
    feather = result.scalars().first()
    
    if not feather:
        return None
    
    if feather_update.status is not None:
        feather.status = feather_update.status
    
    await db.commit()
    await db.refresh(feather)
    return feather
