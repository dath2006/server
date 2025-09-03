from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models import Pages
from app.schemas import PageCreate, PageUpdate


async def get_page(db: AsyncSession, page_id: int) -> Optional[Pages]:
    """Get page by ID"""
    result = await db.execute(
        select(Pages)
        .options(selectinload(Pages.user))
        .where(Pages.id == page_id)
    )
    return result.scalar_one_or_none()


async def get_pages(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    public_only: bool = True,
    show_in_list_only: bool = False
) -> List[Pages]:
    """Get list of pages with optional filters"""
    query = select(Pages).options(selectinload(Pages.user))
    
    if public_only:
        query = query.where(Pages.public == True)
    if show_in_list_only:
        query = query.where(Pages.show_in_list == True)
    
    query = query.offset(skip).limit(limit).order_by(Pages.list_order, Pages.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_page_by_url(db: AsyncSession, url: str) -> Optional[Pages]:
    """Get page by URL"""
    result = await db.execute(
        select(Pages)
        .options(selectinload(Pages.user))
        .where(Pages.url == url)
    )
    return result.scalar_one_or_none()


async def create_page(db: AsyncSession, page: PageCreate, user_id: int) -> Pages:
    """Create new page"""
    db_page = Pages(
        title=page.title,
        body=page.body,
        public=page.public,
        show_in_list=page.show_in_list,
        list_order=page.list_order,
        clean=page.clean,
        url=page.url,
        user_id=user_id,
        parent_id=page.parent_id
    )
    db.add(db_page)
    await db.flush()
    await db.refresh(db_page)
    return db_page


async def update_page(db: AsyncSession, page_id: int, page_update: PageUpdate) -> Optional[Pages]:
    """Update page"""
    update_data = page_update.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Pages)
            .where(Pages.id == page_id)
            .values(**update_data)
        )
        await db.commit()
        return await get_page(db, page_id)
    return await get_page(db, page_id)


async def delete_page(db: AsyncSession, page_id: int) -> bool:
    """Delete page"""
    result = await db.execute(
        delete(Pages).where(Pages.id == page_id)
    )
    await db.commit()
    return result.rowcount > 0
