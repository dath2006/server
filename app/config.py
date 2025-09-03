from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql://username:password@localhost:5432/chyrp_lite"
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Google OAuth settings (for NextAuth.js)
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # Frontend URL
    frontend_url: str = "http://localhost:3000"
    
    # Database settings
    echo_sql: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
