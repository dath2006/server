from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    database_url: str = "postgresql://username:password@localhost:5432/chyrp_lite"
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS settings - Updated to include production domains
    allowed_origins: list[str] = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://chyrp-lite.vercel.app"  # Update with your actual frontend domain
    ]
    
    # Google OAuth settings (for NextAuth.js)
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # Frontend URL
    frontend_url: str = "https://chyrp-lite.vercel.app"
    
    # Backend base URL (for self health checks) - Auto-detect in production
    base_url: str = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    # Database settings
    echo_sql: bool = False
    
    # Cloudinary settings
    cloudinary_cloud_name: Optional[str] = None
    cloudinary_api_key: Optional[str] = None
    cloudinary_api_secret: Optional[str] = None
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
