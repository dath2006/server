from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, Group
from app.schemas import UserSignUp, UserSignIn, GoogleUser, UserResponse
from app.auth import get_password_hash, verify_password
from typing import Optional
import httpx

router = APIRouter(prefix="/auth", tags=["nextauth-authentication"])


@router.post("/signup", response_model=UserResponse)
async def sign_up(user_data: UserSignUp, db: AsyncSession = Depends(get_db)):
    """Sign up with email/password for NextAuth.js"""
    
    # Check if user exists by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_username = result.scalar_one_or_none()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Get default user group (Member)
    result = await db.execute(select(Group).where(Group.name == "Member"))
    user_group = result.scalar_one_or_none()
    group_id = user_group.id if user_group else 2  # Default to Member group (ID: 2)
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.name,
        group_id=group_id,
        approved=True,
        is_active=True
    )
    
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    await db.commit()
    
    return db_user


@router.post("/signin", response_model=UserResponse)
async def sign_in(user_data: UserSignIn, db: AsyncSession = Depends(get_db)):
    """Sign in with email/password for NextAuth.js"""
    
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")
    
    return user


@router.post("/google", response_model=UserResponse)
async def google_auth(google_user: GoogleUser, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth authentication"""
    
    # Check if user exists by email
    result = await db.execute(select(User).where(User.email == google_user.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Check if user exists by google_id
        result = await db.execute(select(User).where(User.google_id == google_user.google_id))
        user = result.scalar_one_or_none()
    
    # Get default user group (Member)
    result = await db.execute(select(Group).where(Group.name == "Member"))
    user_group = result.scalar_one_or_none()
    group_id = user_group.id if user_group else 2  # Default to Member group (ID: 2)
    
    if not user:
        # Create new user
        # Make sure username is unique
        base_username = google_user.username
        username = base_username
        counter = 1
        
        while True:
            result = await db.execute(select(User).where(User.username == username))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                break
            username = f"{base_username}_{counter}"
            counter += 1
        
        user = User(
            email=google_user.email,
            username=username,
            login=username,
            full_name=google_user.name,
            google_id=google_user.google_id,
            image=google_user.image,
            group_id=group_id,
            approved=True,
            is_active=True,
            hashed_password=None  # No password for OAuth User
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        # Update existing user with Google info if not already set
        if not user.google_id:
            user.google_id = google_user.google_id
        if google_user.image and not user.image:
            user.image = google_user.image
        if not user.full_name:
            user.full_name = google_user.name
        user.is_active = True
    
    await db.commit()
    return user


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by ID for NextAuth.js"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("/user-by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """Get user by email for NextAuth.js"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/user/{user_id}", response_model=UserResponse)
async def update_user_profile(
    user_id: int, 
    updates: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update user profile for NextAuth.js"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update allowed fields
    allowed_fields = ["full_name", "image", "website"]
    for field, value in updates.items():
        if field in allowed_fields and hasattr(user, field):
            setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user
