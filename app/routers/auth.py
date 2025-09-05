from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.config import settings
from app.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_active_user, 
    get_user_role,
    get_password_hash
)
from app.schemas import (
    Token, 
    UserResponse, 
    UserSignIn, 
    UserAuthResponse, 
    GoogleUser,
    GoogleUserCreate
)
from app.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signin", response_model=UserAuthResponse)
async def signin(
    user_credentials: UserSignIn,  # email and password
    db: AsyncSession = Depends(get_db)
):
    """Sign in with email and password"""
    # Authenticate user
    user = await authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Get user role based on group_id
    user_role = get_user_role(user.group_id)
    
    # Create access token with user info including role
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user_role  # Include role in token
        },
        expires_delta=access_token_expires
    )
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "website": user.website,
        "image": user.image,
        "group_id": user.group_id,
        "role": user_role,  # Include role in response
        "is_active": user.is_active,
        "approved": user.approved,
        "joined_at": user.joined_at,
        "access_token": access_token,  # Include access token
        "token_type": "bearer"
    }


@router.post("/google", response_model=UserAuthResponse)
async def google_signin(
    google_user: GoogleUserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Sign in with Google OAuth"""
    # Check if user exists by email or google_id
    result = await db.execute(
        select(User).where(
            (User.email == google_user.email) | 
            (User.google_id == google_user.google_id)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            email=google_user.email,
            full_name=google_user.name,
            username=google_user.username,
            google_id=google_user.google_id,
            image=google_user.image,
            group_id=5,  # Default group for new users
            is_active=True,
            approved=True,
            joined_at=datetime.utcnow()
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update existing user info
        user.full_name = google_user.name
        user.image = google_user.image
        await db.commit()
    
    # Get user role
    user_role = get_user_role(user.group_id)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user_role
        },
        expires_delta=access_token_expires
    )
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "website": user.website,
        "image": user.image,
        "group_id": user.group_id,
        "role": user_role,
        "is_active": user.is_active,
        "approved": user.approved,
        "joined_at": user.joined_at,
        "access_token": access_token
    }


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token (backward compatibility)"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_role = get_user_role(user.group_id)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user_role
        }, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return current_user


@router.get("/me/full", response_model=UserAuthResponse) 
async def read_user_full_info(current_user: User = Depends(get_current_active_user)):
    """Get current user info with role"""
    user_role = get_user_role(current_user.group_id)
    
    # Create a new token for the response (optional - for token refresh)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": current_user.email,
            "user_id": current_user.id,
            "role": user_role
        },
        expires_delta=access_token_expires
    )
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "website": current_user.website,
        "image": current_user.image,
        "group_id": current_user.group_id,
        "role": user_role,
        "is_active": current_user.is_active,
        "approved": current_user.approved,
        "joined_at": current_user.joined_at,
        "access_token": access_token,
        "token_type": "bearer"
    }
