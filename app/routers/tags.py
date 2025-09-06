from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.schemas import TagResponse, TagCreate, TagUpdate, PopularTagResponse
from app.crud import tags as tag_crud


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=List[TagResponse])
async def read_tags(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get list of all tags"""
    tags = await tag_crud.get_tags(db, skip=skip, limit=limit)
    return tags


@router.get("/popular", response_model=List[PopularTagResponse])
async def read_popular_tags(
    limit: int = Query(20, ge=1, le=50, description="Number of popular tags to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get popular tags based on usage count"""
    tags = await tag_crud.get_popular_tags(db, limit=limit)
    return tags


@router.get("/{tag_id}", response_model=TagResponse)
async def read_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    """Get tag by ID"""
    tag = await tag_crud.get_tag(db, tag_id=tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.get("/slug/{slug}", response_model=TagResponse)
async def read_tag_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """Get tag by slug"""
    tag = await tag_crud.get_tag_by_slug(db, slug=slug)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/", response_model=TagResponse)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new tag (requires authentication)"""
    # Check if tag already exists
    existing_tag = await tag_crud.get_tag_by_name(db, tag.name)
    if existing_tag:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    return await tag_crud.create_tag(db=db, tag=tag)


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update tag (requires authentication)"""
    tag = await tag_crud.get_tag(db, tag_id=tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Check if new name conflicts with existing tag
    if tag_update.name and tag_update.name != tag.name:
        existing_tag = await tag_crud.get_tag_by_name(db, tag_update.name)
        if existing_tag:
            raise HTTPException(status_code=400, detail="Tag with this name already exists")
    
    updated_tag = await tag_crud.update_tag(db=db, tag_id=tag_id, tag_update=tag_update)
    return updated_tag


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete tag (requires authentication)"""
    tag = await tag_crud.get_tag(db, tag_id=tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    success = await tag_crud.delete_tag(db=db, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete tag")
    
    return {"message": "Tag deleted successfully"}
