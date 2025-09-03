from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.schemas import PageResponse, PageCreate, PageUpdate
from app.crud import pages as page_crud

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("/", response_model=List[PageResponse])
async def read_pages(
    skip: int = 0,
    limit: int = 100,
    public_only: bool = Query(True, description="Show only public pages"),
    show_in_list_only: bool = Query(False, description="Show only pages marked for listing"),
    db: AsyncSession = Depends(get_db)
):
    """Get list of pages"""
    pages = await page_crud.get_pages(
        db, skip=skip, limit=limit, 
        public_only=public_only, 
        show_in_list_only=show_in_list_only
    )
    return pages


@router.get("/by-url/{url}", response_model=PageResponse)
async def read_page_by_url(url: str, db: AsyncSession = Depends(get_db)):
    """Get page by URL"""
    page = await page_crud.get_page_by_url(db, url=url)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.get("/{page_id}", response_model=PageResponse)
async def read_page(page_id: int, db: AsyncSession = Depends(get_db)):
    """Get page by ID"""
    page = await page_crud.get_page(db, page_id=page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/", response_model=PageResponse)
async def create_page(
    page: PageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new page"""
    return await page_crud.create_page(db=db, page=page, user_id=current_user.id)


@router.put("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: int,
    page_update: PageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update page"""
    page = await page_crud.get_page(db, page_id=page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Check if user owns the page or has admin privileges
    if page.user_id != current_user.id:
        # You can add admin role check here
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    updated_page = await page_crud.update_page(db=db, page_id=page_id, page_update=page_update)
    return updated_page


@router.delete("/{page_id}")
async def delete_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete page"""
    page = await page_crud.get_page(db, page_id=page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Check if user owns the page or has admin privileges
    if page.user_id != current_user.id:
        # You can add admin role check here
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    success = await page_crud.delete_page(db=db, page_id=page_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete page")
    
    return {"message": "Page deleted successfully"}
