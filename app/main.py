from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import asyncio
import aiohttp
import logging
from app.config import settings
from app.routers import auth, users, posts, nextauth, tags, settings as settings_router, comments, categories, permissions
from app.routers.admin import router as admin_router
from app.database import get_db
from app.crud import posts as post_crud
from app.utils import format_post_for_api

app = FastAPI(
    title="Chryp Lite Reimagined CMS API",
    description="A modern FastAPI backend for Chryp Lite CMS with NextAuth.js support",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store the health check task
health_check_task = None

# CORS middleware - Updated for NextJS frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "http://localhost:3001",  # Alternative Next.js port
        "https://your-frontend-domain.com"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")  # Existing JWT auth
app.include_router(nextauth.router, prefix="/api/v1")  # NextAuth.js compatible routes
app.include_router(users.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")  # Comments route
app.include_router(categories.router, prefix="/api/v1")  # Categories route
# app.include_router(pages.router, prefix="/api/v1")  # Disabled for now - no pages table
app.include_router(tags.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")  # Global settings route
app.include_router(permissions.router, prefix="/api/v1")  # Permissions route
app.include_router(admin_router, prefix="/api/v1")  # Admin routes


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Chryp Lite Reimagined CMS API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


async def self_health_check():
    """Background task that calls the health endpoint every 50 seconds"""
    while True:
        try:
            await asyncio.sleep(50)  # Wait 50 seconds
            async with aiohttp.ClientSession() as session:
                # Try to determine the base URL
                base_url = getattr(settings, 'base_url', 'http://localhost:8000')
                health_url = f"{base_url}/health"
                
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        logger.info("Health check successful")
                    else:
                        logger.warning(f"Health check returned status: {response.status}")
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Start the self-health-check background task"""
    global health_check_task
    health_check_task = asyncio.create_task(self_health_check())
    logger.info("Self-health-check task started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up the health check task on shutdown"""
    global health_check_task
    if health_check_task:
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
        logger.info("Self-health-check task cancelled")