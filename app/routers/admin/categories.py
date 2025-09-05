from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_admin_user
from app.models import User
from app.schemas import (
    CreateCategoryData, 
    UpdateCategoryData, 
    AdminCategoryResponse, 
    AdminCategoriesResponse,
    CategoryStatsResponse,
    BulkDeleteRequest,
    ReorderCategoriesRequest,
    CategoryPaginationInfo,
    CategoryFilters
)
from app.crud import categories as crud_categories
import math

router = APIRouter()


@router.get("/categories", response_model=AdminCategoriesResponse)
async def get_admin_categories(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of categories per page"),
    search: Optional[str] = Query(None, description="Search in category name or description"),
    is_listed: Optional[bool] = Query(None, description="Filter by visibility status"),
    sort_by: str = Query("name", description="Sort by field (name, created_at, updated_at, display_order, post_count)"),
    sort_order: str = Query("asc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get categories for admin panel with pagination, filtering, and sorting"""
    
    categories, total_categories = await crud_categories.get_categories_with_pagination(
        db=db,
        page=page,
        limit=limit,
        search=search,
        is_listed=is_listed,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Calculate pagination info
    total_pages = math.ceil(total_categories / limit) if total_categories > 0 else 1
    has_next = page < total_pages
    has_previous = page > 1
    next_page = page + 1 if has_next else None
    previous_page = page - 1 if has_previous else None
    
    # Convert to response format
    category_responses = []
    for category in categories:
        category_response = AdminCategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            is_listed=category.is_listed,
            display_order=category.display_order,
            post_count=getattr(category, 'post_count', 0),
            created_at=category.created_at,
            updated_at=category.updated_at
        )
        category_responses.append(category_response)
    
    pagination = CategoryPaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_categories=total_categories,
        limit=limit,
        has_next=has_next,
        has_previous=has_previous,
        next_page=next_page,
        previous_page=previous_page
    )
    
    filters = CategoryFilters(
        search=search,
        is_listed=is_listed
    )
    
    return AdminCategoriesResponse(
        data=category_responses,
        pagination=pagination,
        filters=filters
    )


@router.get("/categories/search", response_model=List[AdminCategoryResponse])
async def search_admin_categories(
    q: str = Query(..., description="Search query"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Search categories"""
    
    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters long"
        )
    
    categories = await crud_categories.search_categories(db, q)
    
    return [
        AdminCategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            is_listed=category.is_listed,
            display_order=category.display_order,
            post_count=0,  # For search results, we'll skip post count for performance
            created_at=category.created_at,
            updated_at=category.updated_at
        )
        for category in categories
    ]


@router.get("/categories/stats", response_model=CategoryStatsResponse)
async def get_category_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get category statistics"""
    
    stats = await crud_categories.get_category_stats(db)
    
    return CategoryStatsResponse(
        total=stats["total"],
        listed=stats["listed"],
        unlisted=stats["unlisted"],
        total_posts=stats["total_posts"]
    )


@router.get("/categories/{category_id}", response_model=AdminCategoryResponse)
async def get_admin_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get specific category by ID"""
    
    category = await crud_categories.get_category(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Get post count
    categories_with_count, _ = await crud_categories.get_categories_with_pagination(
        db=db,
        page=1,
        limit=1
    )
    post_count = 0
    if categories_with_count:
        for cat in categories_with_count:
            if cat.id == category_id:
                post_count = getattr(cat, 'post_count', 0)
                break
    
    return AdminCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        is_listed=category.is_listed,
        display_order=category.display_order,
        post_count=post_count,
        created_at=category.created_at,
        updated_at=category.updated_at
    )


@router.post("/categories", response_model=AdminCategoryResponse)
async def create_admin_category(
    category_data: CreateCategoryData,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create new category"""
    
    try:
        category = await crud_categories.create_category(
            db=db, 
            category=category_data, 
            user_id=current_admin.id
        )
        
        return AdminCategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            is_listed=category.is_listed,
            display_order=category.display_order,
            post_count=0,
            created_at=category.created_at,
            updated_at=category.updated_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create category: {str(e)}"
        )


@router.put("/categories/{category_id}", response_model=AdminCategoryResponse)
async def update_admin_category(
    category_id: int,
    category_data: UpdateCategoryData,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update existing category"""
    
    category = await crud_categories.update_category(
        db=db,
        category_id=category_id,
        category_update=category_data
    )
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Get post count
    categories_with_count, _ = await crud_categories.get_categories_with_pagination(
        db=db,
        page=1,
        limit=1
    )
    post_count = 0
    if categories_with_count:
        for cat in categories_with_count:
            if cat.id == category_id:
                post_count = getattr(cat, 'post_count', 0)
                break
    
    return AdminCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        is_listed=category.is_listed,
        display_order=category.display_order,
        post_count=post_count,
        created_at=category.created_at,
        updated_at=category.updated_at
    )


@router.delete("/categories/{category_id}")
async def delete_admin_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete single category"""
    
    success = await crud_categories.delete_category(db, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {"message": "Category deleted successfully"}


@router.delete("/categories")
async def bulk_delete_admin_categories(
    request: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Bulk delete categories"""
    
    if not request.ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No category IDs provided"
        )
    
    deleted_count = await crud_categories.bulk_delete_categories(db, request.ids)
    
    return {
        "message": f"{deleted_count} categories deleted successfully",
        "deleted_count": deleted_count
    }


@router.patch("/categories/{category_id}/toggle-visibility", response_model=AdminCategoryResponse)
async def toggle_category_visibility(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Toggle category visibility"""
    
    category = await crud_categories.toggle_category_visibility(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Get post count
    categories_with_count, _ = await crud_categories.get_categories_with_pagination(
        db=db,
        page=1,
        limit=1
    )
    post_count = 0
    if categories_with_count:
        for cat in categories_with_count:
            if cat.id == category_id:
                post_count = getattr(cat, 'post_count', 0)
                break
    
    return AdminCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        is_listed=category.is_listed,
        display_order=category.display_order,
        post_count=post_count,
        created_at=category.created_at,
        updated_at=category.updated_at
    )


@router.put("/categories/reorder")
async def reorder_categories(
    request: ReorderCategoriesRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Reorder categories"""
    
    if not request.category_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No category IDs provided"
        )
    
    success = await crud_categories.reorder_categories(db, request.category_ids)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reorder categories"
        )
    
    return {"message": "Categories reordered successfully"}
