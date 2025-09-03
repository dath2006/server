from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models import User
from app.schemas import UserCreate, UserUpdate
from app.auth import get_password_hash


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.group))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.group))
        .where(User.email == email)
    )
    return result.scalar_one_or_none()


# Removed get_user_by_login (obsolete)


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.group))
        .where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.group))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Create new user"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        website=user.website,
        group_id=user.group_id,
        approved=user.approved,
        is_active=True,
        google_id=user.google_id if hasattr(user, 'google_id') else None,
        image=user.image if hasattr(user, 'image') else None
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Update user"""
    update_data = user_update.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await db.commit()
        return await get_user(db, user_id)
    return await get_user(db, user_id)


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user"""
    result = await db.execute(
        delete(User).where(User.id == user_id)
    )
    await db.commit()
    return result.rowcount > 0
