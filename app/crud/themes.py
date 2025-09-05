from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from app.models import Theme

async def get_themes(db: AsyncSession) -> List[Theme]:
    """Get all themes"""
    result = await db.execute(select(Theme).order_by(Theme.name))
    return result.scalars().all()

async def get_theme_by_id(db: AsyncSession, theme_id: int) -> Optional[Theme]:
    """Get a theme by ID"""
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    return result.scalars().first()

async def activate_theme(db: AsyncSession, theme_id: int) -> Optional[Theme]:
    """Activate a theme (deactivate all others first)"""
    # First, deactivate all themes
    await db.execute(update(Theme).values(isActive=False))
    
    # Then activate the selected theme
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    theme = result.scalars().first()
    
    if not theme:
        return None
    
    theme.isActive = True
    await db.commit()
    await db.refresh(theme)
    return theme
