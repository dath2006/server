from fastapi import APIRouter
from app.routers.admin import posts, users, groups, uploads, tags, categories, comments, spam, settings, modules, feathers, themes

router = APIRouter()

# Include all admin sub-routers with /admin prefix
router.include_router(posts.router, prefix="/admin", tags=["admin-posts"])
router.include_router(users.router, prefix="/admin", tags=["admin-users"])
router.include_router(groups.router, prefix="/admin", tags=["admin-groups"])
router.include_router(uploads.router, prefix="/admin", tags=["admin-uploads"])
router.include_router(tags.router, prefix="/admin", tags=["admin-tags"])
router.include_router(categories.router, prefix="/admin", tags=["admin-categories"])
router.include_router(comments.router, prefix="/admin", tags=["admin-comments"])
router.include_router(spam.router, prefix="/admin", tags=["admin-spam"])
router.include_router(settings.router, prefix="/admin", tags=["admin-settings"])
router.include_router(modules.router, prefix="/admin", tags=["admin-modules"])
router.include_router(feathers.router, prefix="/admin", tags=["admin-feathers"])
router.include_router(themes.router, prefix="/admin", tags=["admin-themes"])

# Export router for use in main application
__all__ = ["router"]
