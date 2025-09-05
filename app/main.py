from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from app.config import settings
from app.routers import auth, users, posts, nextauth, tags, settings as settings_router  # pages disabled for now
from app.routers.admin import router as admin_router
from app.database import get_db
from app.crud import posts as post_crud
from app.utils import format_post_for_api

app = FastAPI(
    title="Chryp Lite Reimagined CMS API",
    description="A modern FastAPI backend for Chryp Lite CMS with NextAuth.js support",
    version="1.0.0"
)

# CORS middleware - Updated for NextJS frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "http://localhost:3001",  # Alternative Next.js port
        "https://your-frontend-domain.com"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")  # Existing JWT auth
app.include_router(nextauth.router, prefix="/api/v1")  # NextAuth.js compatible routes
app.include_router(users.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
# app.include_router(pages.router, prefix="/api/v1")  # Disabled for now - no pages table
app.include_router(tags.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")  # Global settings route
app.include_router(admin_router, prefix="/api/v1")  # Admin routes


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Chryp Lite Reimagined CMS API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}