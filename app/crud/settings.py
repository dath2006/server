
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from app.models import Setting
from app.schemas import SettingCreate, SettingUpdate

async def get_settings(db: AsyncSession) -> List[Setting]:
    """Get all settings"""
    result = await db.execute(select(Setting).order_by(Setting.name))
    return result.scalars().all()

async def get_setting_by_name(db: AsyncSession, name: str) -> Optional[Setting]:
    """Get a setting by name"""
    result = await db.execute(select(Setting).where(Setting.name == name))
    return result.scalars().first()

async def get_setting_by_id(db: AsyncSession, setting_id: int) -> Optional[Setting]:
    """Get a setting by ID"""
    result = await db.execute(select(Setting).where(Setting.id == setting_id))
    return result.scalars().first()

async def create_setting(db: AsyncSession, setting: SettingCreate) -> Setting:
    """Create a new setting"""
    db_setting = Setting(
        name=setting.name,
        value=setting.value,
        description=setting.description,
        type=setting.type
    )
    db.add(db_setting)
    await db.commit()
    await db.refresh(db_setting)
    return db_setting

async def update_setting(db: AsyncSession, setting: Setting, setting_update: SettingUpdate) -> Setting:
    """Update an existing setting"""
    update_data = setting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)
    await db.commit()
    await db.refresh(setting)
    return setting

async def update_setting_by_name(db: AsyncSession, name: str, value: str, 
                          setting_type: Optional[str] = None, 
                          description: Optional[str] = None) -> Optional[Setting]:
    """Update a setting by name, create if it doesn't exist"""
    setting = await get_setting_by_name(db, name)
    if setting:
        # Update existing setting
        setting.value = value
        if setting_type is not None:
            setting.type = setting_type
        if description is not None:
            setting.description = description
        await db.commit()
        await db.refresh(setting)
        return setting
    else:
        # Create new setting
        new_setting = SettingCreate(
            name=name,
            value=value,
            type=setting_type or "string",
            description=description
        )
        return await create_setting(db, new_setting)

async def update_multiple_settings(db: AsyncSession, settings_data: Dict[str, Dict[str, Any]]) -> List[Setting]:
    """Update multiple settings at once"""
    updated_settings = []
    for name, data in settings_data.items():
        value = data.get("value", "")
        setting_type = data.get("type", "string")
        description = data.get("description")
        setting = await update_setting_by_name(db, name, value, setting_type, description)
        if setting:
            updated_settings.append(setting)
    return updated_settings

async def delete_setting(db: AsyncSession, setting: Setting) -> bool:
    """Delete a setting"""
    try:
        await db.delete(setting)
        await db.commit()
        return True
    except Exception:
        await db.rollback()
        return False

async def get_settings_by_type(db: AsyncSession, setting_type: str) -> List[Setting]:
    """Get settings by type"""
    result = await db.execute(select(Setting).where(Setting.type == setting_type).order_by(Setting.name))
    return result.scalars().all()
