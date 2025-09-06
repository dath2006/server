from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, delete, or_
from sqlalchemy.orm import selectinload
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import mimetypes
import json
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Upload, Post
from app.services import upload_file_with_fallback, delete_file_with_fallback

router = APIRouter()


@router.get("/uploads", response_model=Dict[str, Any])
async def get_admin_uploads(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of uploads per page"),
    search: Optional[str] = Query(None, description="Search in file name"),
    mediaType: Optional[str] = Query(None, description="Filter by media type: image, video, audio, file"),
    sortBy: Optional[str] = Query("uploadedAt", description="Sort by field: uploadedAt, fileName, size"),
    sortOrder: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get uploads for admin panel with pagination and filtering"""
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Base query with user relationship
    query = select(Upload).options(
        selectinload(Upload.user),
        selectinload(Upload.post)
    )
    
    # Apply filters
    conditions = []
    
    # Search filter for file name
    if search:
        search_term = f"%{search}%"
        conditions.append(Upload.name.ilike(search_term))
    
    # Media type filter
    if mediaType:
        # Map mediaType to Upload.type values
        type_mapping = {
            "image": "image",
            "video": "video", 
            "audio": "audio",
            "file": "file"
        }
        
        if mediaType in type_mapping:
            conditions.append(Upload.type == type_mapping[mediaType])
    
    # Apply all conditions
    if conditions:
        for condition in conditions:
            query = query.where(condition)
    
    # Get total count for pagination
    count_query = select(func.count(Upload.id))
    if conditions:
        for condition in conditions:
            count_query = count_query.where(condition)
    
    total_result = await db.execute(count_query)
    total_uploads = total_result.scalar()
    
    # Apply sorting
    sort_field = Upload.uploaded_at  # Default to uploadedAt (uploaded_at)
    if sortBy == "fileName":
        sort_field = Upload.name
    elif sortBy == "size":
        sort_field = Upload.size
    elif sortBy == "uploadedAt":
        sort_field = Upload.uploaded_at
    
    if sortOrder == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    uploads = result.scalars().all()
    
    # Process uploads into required format
    uploads_data = []
    for upload in uploads:
        # Map upload type to mediaType
        media_type_mapping = {
            "image": "image",
            "video": "video",
            "audio": "audio", 
            "file": "file",
            "caption": "file"  # Captions are treated as files
        }
        
        media_type = media_type_mapping.get(upload.type, "file")
        
        upload_data = {
            "id": str(upload.id),
            "fileName": upload.name,
            "uploadedAt": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
            "uploader": {
                "name": upload.user.full_name if upload.user and upload.user.full_name else (upload.user.username if upload.user else "Unknown")
            },
            "size": upload.size or 0,
            "mediaType": media_type,
            "mimeType": upload.mime_type or "application/octet-stream",
            "url": upload.url,
            "isLinkedToPost": upload.post_id is not None
        }
        
        uploads_data.append(upload_data)
    
    # Calculate pagination metadata
    total_pages = (total_uploads + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        "data": uploads_data,
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalUploads": total_uploads,
            "limit": limit,
            "hasNext": has_next,
            "hasPrevious": has_previous,
            "nextPage": page + 1 if has_next else None,
            "previousPage": page - 1 if has_previous else None
        },
        "filters": {
            "search": search,
            "mediaType": mediaType,
            "sortBy": sortBy,
            "sortOrder": sortOrder
        }
    }


@router.get("/uploads/{upload_id}", response_model=Dict[str, Any])
async def get_admin_upload(
    upload_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single upload for admin panel"""
    query = select(Upload).options(
        selectinload(Upload.user),
        selectinload(Upload.post)
    ).where(Upload.id == upload_id)
    
    result = await db.execute(query)
    upload = result.scalar_one_or_none()
    
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Map upload type to mediaType
    media_type_mapping = {
        "image": "image",
        "video": "video",
        "audio": "audio", 
        "file": "file",
        "caption": "file"
    }
    
    media_type = media_type_mapping.get(upload.type, "file")

    upload_data = {
        "id": str(upload.id),
        "fileName": upload.name,
        "uploadedAt": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
        "uploader": {
            "name": upload.user.full_name if upload.user and upload.user.full_name else (upload.user.username if upload.user else "Unknown"),
            "id": str(upload.user.id) if upload.user else None,
            "username": upload.user.username if upload.user else None
        },
        "size": upload.size or 0,
        "mediaType": media_type,
        "mimeType": upload.mime_type or "application/octet-stream",
        "url": upload.url,
        "isLinkedToPost": upload.post_id is not None,
        "linkedPost": {
            "id": str(upload.post.id),
            "title": upload.post.title,
            "type": upload.post.type
        } if upload.post else None
    }
    
    return upload_data


@router.get("/uploads/stats", response_model=Dict[str, Any])
async def get_uploads_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get uploads statistics for admin dashboard"""
    
    # Total uploads
    total_uploads_result = await db.execute(select(func.count(Upload.id)))
    total_uploads = total_uploads_result.scalar()
    
    # Uploads by type
    type_query = select(
        Upload.type,
        func.count(Upload.id).label('count')
    ).group_by(Upload.type)
    
    type_result = await db.execute(type_query)
    uploads_by_type = {row.type: row.count for row in type_result}
    
    # Total storage used
    storage_result = await db.execute(
        select(func.sum(Upload.size))
    )
    total_storage = storage_result.scalar() or 0
    
    # Recent uploads (uploaded in last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_uploads_result = await db.execute(
        select(func.count(Upload.id))
        .where(Upload.uploaded_at >= thirty_days_ago)
    )
    recent_uploads = recent_uploads_result.scalar()
    
    # Orphaned uploads (not linked to any post)
    orphaned_uploads_result = await db.execute(
        select(func.count(Upload.id))
        .where(Upload.post_id.is_(None))
    )
    orphaned_uploads = orphaned_uploads_result.scalar()
    
    return {
        "totalUploads": total_uploads,
        "uploadsByType": uploads_by_type,
        "totalStorageBytes": total_storage,
        "totalStorageMB": round(total_storage / (1024 * 1024), 2) if total_storage else 0,
        "recentUploads": recent_uploads,
        "orphanedUploads": orphaned_uploads,
        "generatedAt": datetime.utcnow().isoformat()
    }


# Helper functions for file upload
def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with UUID prefix"""
    ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return unique_name


async def save_upload_file(file: UploadFile, upload_type: str) -> tuple[str, Dict[str, Any]]:
    """Save uploaded file using Cloudinary with local fallback and return file URL and metadata"""
    if not file:
        return None, {}
    
    try:
        # Use the new Cloudinary service with fallback
        file_url, metadata = await upload_file_with_fallback(file, f"uploads/{upload_type}")
        return file_url, metadata
    except Exception as e:
        # Final fallback to local storage
        upload_dir = Path("uploads") / upload_type
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return str(file_path), {'is_cloudinary': False, 'local_path': str(file_path)}


def determine_upload_type(mime_type: str) -> str:
    """Determine upload type based on MIME type"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    else:
        return 'file'


@router.post("/uploads", response_model=Dict[str, Any])
async def create_admin_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new upload (standalone, not linked to any post)"""
    
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        # Determine MIME type and upload type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = file.content_type or "application/octet-stream"
        
        upload_type = determine_upload_type(mime_type)
        
        # Save file using Cloudinary with local fallback
        file_url, metadata = await save_upload_file(file, f"{upload_type}s")  # images, videos, audios, files
        
        # Get file size from metadata or file
        file_size = metadata.get('size', 0)
        if file_size == 0 and hasattr(file, 'size'):
            file_size = file.size
        elif file_size == 0 and not metadata.get('is_cloudinary'):
            # For local files, get size from saved file
            local_path = metadata.get('local_path')
            if local_path and Path(local_path).exists():
                file_size = Path(local_path).stat().st_size
        
        # Create upload record in database
        upload = Upload(
            url=file_url,
            user_id=current_user.id,
            post_id=None,  # Not linked to any post
            type=upload_type,
            size=file_size,
            name=file.filename,
            mime_type=mime_type,
            metadata=json.dumps(metadata) if metadata else None  # Store metadata for future use
        )
        
        db.add(upload)
        await db.commit()
        
        # Map upload type to mediaType for response
        media_type_mapping = {
            "image": "image",
            "video": "video",
            "audio": "audio", 
            "file": "file"
        }
        
        media_type = media_type_mapping.get(upload_type, "file")
        
        response_data = {
            "id": str(upload.id),
            "fileName": upload.name,
            "uploadedAt": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
            "uploader": {
                "name": current_user.full_name if current_user.full_name else current_user.username
            },
            "size": upload.size or 0,
            "mediaType": media_type,
            "mimeType": upload.mime_type,
            "url": upload.url,
            "isLinkedToPost": False,
            "message": "Upload created successfully"
        }
        
        # Add Cloudinary-specific information if available
        if metadata.get('is_cloudinary'):
            response_data.update({
                "cloudinary": {
                    "public_id": metadata.get('public_id'),
                    "resource_type": metadata.get('resource_type'),
                    "format": metadata.get('format'),
                    "version": metadata.get('version')
                }
            })
        
        return response_data
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error creating upload: {str(e)}")


@router.delete("/uploads/{upload_id}", response_model=Dict[str, Any])
async def delete_admin_upload(
    upload_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an upload if it's not linked to any post"""
    
    # Check if upload exists
    result = await db.execute(
        select(Upload).options(
            selectinload(Upload.post),
            selectinload(Upload.user)
        ).where(Upload.id == upload_id)
    )
    existing_upload = result.scalar_one_or_none()
    
    if not existing_upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Check if upload is linked to a post
    if existing_upload.post_id is not None:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete upload that is linked to post ID {existing_upload.post_id}. Please delete the post first or unlink the upload."
        )
    
    try:
        # Delete the physical file from filesystem
        deleted_file_path = None
        if existing_upload.url:
            file_path = existing_upload.url.lstrip('/')  # Remove leading slash
            full_path = Path(file_path)
            if full_path.exists():
                try:
                    full_path.unlink()  # Delete the file
                    deleted_file_path = str(full_path)
                except OSError as e:
                    # Log the error but continue with database deletion
                    print(f"Warning: Could not delete file {full_path}: {e}")
        
        # Delete the upload record from database
        await db.execute(delete(Upload).where(Upload.id == upload_id))
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Upload deleted successfully",
            "deletedUpload": {
                "id": str(existing_upload.id),
                "fileName": existing_upload.name,
                "size": existing_upload.size,
                "mediaType": existing_upload.type,
                "uploader": existing_upload.user.username if existing_upload.user else "Unknown"
            },
            "deletedFile": deleted_file_path
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting upload: {str(e)}")


@router.put("/uploads/{upload_id}", response_model=Dict[str, Any])
async def update_admin_upload(
    upload_id: int,
    upload_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update upload metadata (mainly fileName)"""
    
    # Check if upload exists
    result = await db.execute(
        select(Upload).options(
            selectinload(Upload.user),
            selectinload(Upload.post)
        ).where(Upload.id == upload_id)
    )
    existing_upload = result.scalar_one_or_none()
    
    if not existing_upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    try:
        # Update fileName if provided
        if "fileName" in upload_data and upload_data["fileName"]:
            existing_upload.name = upload_data["fileName"]
        
        # Update other metadata if needed
        if "mimeType" in upload_data:
            existing_upload.mime_type = upload_data["mimeType"]
        
        await db.commit()
        
        # Map upload type to mediaType for response
        media_type_mapping = {
            "image": "image",
            "video": "video",
            "audio": "audio", 
            "file": "file",
            "caption": "file"
        }
        
        media_type = media_type_mapping.get(existing_upload.type, "file")
        
        return {
            "id": str(existing_upload.id),
            "fileName": existing_upload.name,
            "uploadedAt": existing_upload.uploaded_at.isoformat() if existing_upload.uploaded_at else None,
            "uploader": {
                "name": existing_upload.user.full_name if existing_upload.user and existing_upload.user.full_name else (existing_upload.user.username if existing_upload.user else "Unknown")
            },
            "size": existing_upload.size or 0,
            "mediaType": media_type,
            "mimeType": existing_upload.mime_type or "application/octet-stream",
            "url": existing_upload.url,
            "isLinkedToPost": existing_upload.post_id is not None,
            "message": "Upload updated successfully"
        }
    
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error updating upload: {str(e)}")


@router.post("/uploads/cleanup", response_model=Dict[str, Any])
async def cleanup_orphaned_uploads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Clean up orphaned uploads (uploads not linked to any post)"""
    
    try:
        # Find orphaned uploads
        result = await db.execute(
            select(Upload).where(Upload.post_id.is_(None))
        )
        orphaned_uploads = result.scalars().all()
        
        if not orphaned_uploads:
            return {
                "success": True,
                "message": "No orphaned uploads found",
                "cleanedCount": 0,
                "deletedFiles": []
            }
        
        deleted_files = []
        cleaned_count = 0
        
        for upload in orphaned_uploads:
            # Delete physical file
            if upload.url:
                file_path = upload.url.lstrip('/')
                full_path = Path(file_path)
                if full_path.exists():
                    try:
                        full_path.unlink()
                        deleted_files.append(str(full_path))
                    except OSError as e:
                        print(f"Warning: Could not delete file {full_path}: {e}")
            
            # Delete database record
            await db.execute(delete(Upload).where(Upload.id == upload.id))
            cleaned_count += 1
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Successfully cleaned up {cleaned_count} orphaned uploads",
            "cleanedCount": cleaned_count,
            "deletedFiles": deleted_files
        }
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning up uploads: {str(e)}")
