from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.schemas import UserResponse, UserCreate, UserUpdate, UserProfile, UpdateProfileData, ChangePasswordData, ApiResponse
from app.crud import users as user_crud
from app.utils import save_uploaded_file, format_user_profile
from app.services import upload_file_with_fallback

router = APIRouter(prefix="/users", tags=["users"])

# New user profile endpoints
@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user profile by ID"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return format_user_profile(user)


@router.put("/{user_id}", response_model=UserProfile)
async def update_user_profile(
    user_id: int,
    profile_data: UpdateProfileData,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user profile"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert to dict and update
    update_data = profile_data.model_dump(exclude_unset=True)
    updated_user = await user_crud.update_user_profile(db=db, user_id=user_id, profile_data=update_data)
    
    if updated_user is None:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    
    return format_user_profile(updated_user)


@router.put("/{user_id}/password", response_model=ApiResponse)
async def change_user_password(
    user_id: int,
    password_data: ChangePasswordData,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Change user password"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        await user_crud.change_user_password(db=db, user_id=user_id, password_data=password_data)
        return ApiResponse(message="Password updated successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.put("/{user_id}/avatar")
async def update_user_avatar(
    user_id: int,
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user avatar"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check file type
    if not avatar.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Upload to Cloudinary with local fallback
        file_url, metadata = await upload_file_with_fallback(avatar, "uploads/avatars")
        
        # Update user avatar
        updated_user = await user_crud.update_user_avatar(db=db, user_id=user_id, avatar_url=file_url)
        
        if updated_user is None:
            raise HTTPException(status_code=400, detail="Failed to update avatar")
        
        response_data = {
            "avatar_url": file_url,
            "message": "Avatar updated successfully"
        }
        
        # Add Cloudinary-specific information if available
        if metadata.get('is_cloudinary'):
            response_data.update({
                "cloudinary": {
                    "public_id": metadata.get('public_id'),
                    "resource_type": metadata.get('resource_type'),
                    "format": metadata.get('format')
                }
            })
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update avatar: {str(e)}")


@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_user_account(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete user account"""
    user = await user_crud.get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = await user_crud.delete_user(db=db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete account")
    
    return ApiResponse(message="Account deleted successfully")


# Legacy endpoints (keeping for backward compatibility)


# @router.get("/", response_model=List[UserResponse])
# async def read_users(
#     skip: int = 0, 
#     limit: int = 100, 
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get list of users"""
#     users = await user_crud.get_users(db, skip=skip, limit=limit)
#     return users


# @router.get("/{user_id}", response_model=UserResponse)
# async def read_user(
#     user_id: int, 
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Get user by ID"""
#     user = await user_crud.get_user(db, user_id=user_id)
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user


# @router.post("/", response_model=UserResponse)
# async def create_user(
#     user: UserCreate, 
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Create new user"""
#     # Check if user already exists
#     existing_user = await user_crud.get_user_by_username(db, username=user.username)
#     if existing_user:
#         raise HTTPException(status_code=400, detail="Username already registered")
#     existing_email = await user_crud.get_user_by_email(db, email=user.email)
#     if existing_email:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return await user_crud.create_user(db=db, user=user)


# @router.put("/{user_id}", response_model=UserResponse)
# async def update_user(
#     user_id: int,
#     user_update: UserUpdate,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Update user"""
#     user = await user_crud.get_user(db, user_id=user_id)
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     updated_user = await user_crud.update_user(db=db, user_id=user_id, user_update=user_update)
#     return updated_user


# @router.delete("/{user_id}")
# async def delete_user(
#     user_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """Delete user"""
#     user = await user_crud.get_user(db, user_id=user_id)
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     success = await user_crud.delete_user(db=db, user_id=user_id)
#     if not success:
#         raise HTTPException(status_code=400, detail="Failed to delete user")
    
#     return {"message": "User deleted successfully"}
