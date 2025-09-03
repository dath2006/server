from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.schemas import UserResponse, UserCreate, UserUpdate
from app.crud import users as user_crud

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of users"""
    users = await user_crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user by ID"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new user"""
    # Check if user already exists
    existing_user = await user_crud.get_user_by_username(db, username=user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    existing_email = await user_crud.get_user_by_email(db, email=user.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await user_crud.create_user(db=db, user=user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = await user_crud.update_user(db=db, user_id=user_id, user_update=user_update)
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete user"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    success = await user_crud.delete_user(db=db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete user")
    
    return {"message": "User deleted successfully"}
