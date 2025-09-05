"""
Sample settings data for testing the /api/v1/settings endpoint
Run this script to populate the database with sample settings
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, engine
from app.crud import settings as settings_crud
from app.models import Setting, Theme, Module, Feather
import json

async def create_sample_settings():
    """Create sample settings data"""
    
    async with AsyncSession(engine) as db:
        # Sample settings data
        sample_settings = [
            # Basic site settings
            ("site_title", "My Awesome Blog", "string", "The title of your site"),
            ("site_description", "A blog about awesome things", "string", "Description of your site"),
            ("site_url", "https://myblog.com", "string", "The URL of your site"),
            ("timezone", "UTC", "string", "Site timezone"),
            ("locale", "en", "string", "Site language locale"),
            
            # Content settings
            ("posts_per_page", "10", "number", "Number of posts to show per page"),
            ("enable_registration", "true", "boolean", "Allow new user registration"),
            ("enable_comments", "true", "boolean", "Enable comments on posts"),
            ("enable_trackbacks", "false", "boolean", "Enable trackbacks"),
            ("enable_webmentions", "true", "boolean", "Enable webmentions"),
            ("enable_feeds", "true", "boolean", "Enable RSS/Atom feeds"),
            ("enable_search", "true", "boolean", "Enable search functionality"),
            ("maintenance_mode", "false", "boolean", "Site maintenance mode"),
            
            # Admin settings (sensitive)
            ("admin_email", "admin@myblog.com", "string", "Administrator email"),
            ("smtp_host", "smtp.gmail.com", "string", "SMTP server host"),
            ("smtp_port", "587", "number", "SMTP server port"),
            ("smtp_username", "user@gmail.com", "string", "SMTP username"),
            ("smtp_password", "encrypted_password", "string", "SMTP password"),
            ("smtp_encryption", "tls", "string", "SMTP encryption type"),
            
            # Social links (JSON)
            ("social_links", json.dumps({
                "facebook": "https://facebook.com/myblog",
                "twitter": "https://twitter.com/myblog",
                "instagram": "https://instagram.com/myblog",
                "linkedin": "",
                "github": "https://github.com/myblog"
            }), "json", "Social media links"),
            
            # SEO settings (JSON)
            ("seo_settings", json.dumps({
                "meta_description": "Default meta description for the site",
                "meta_keywords": "blog, awesome, content, cms",
                "og_image": "https://myblog.com/og-image.jpg"
            }), "json", "SEO and meta settings"),
        ]
        
        # Create settings
        for name, value, setting_type, description in sample_settings:
            await settings_crud.update_setting_by_name(
                db, name, value, setting_type, description
            )
            print(f"Created/updated setting: {name}")
        
        # Sample themes
        sample_themes = [
            {"name": "default", "description": "Default theme", "isActive": True},
            {"name": "dark", "description": "Dark theme", "isActive": False},
            {"name": "minimal", "description": "Minimal theme", "isActive": False},
        ]
        
        for theme_data in sample_themes:
            theme = Theme(**theme_data)
            db.add(theme)
        
        # Sample modules
        sample_modules = [
            {
                "name": "comments",
                "description": "Comment system module",
                "status": "enabled",
                "canDisable": True,
                "canUninstall": False,
                "conflicts": None
            },
            {
                "name": "search",
                "description": "Search functionality module",
                "status": "enabled",
                "canDisable": True,
                "canUninstall": True,
                "conflicts": None
            },
            {
                "name": "feeds",
                "description": "RSS/Atom feed module",
                "status": "enabled",
                "canDisable": True,
                "canUninstall": True,
                "conflicts": None
            }
        ]
        
        for module_data in sample_modules:
            module = Module(**module_data)
            db.add(module)
        
        # Sample feathers (post types)
        sample_feathers = [
            {
                "name": "text",
                "description": "Basic text posts",
                "status": "enabled",
                "canDisable": False
            },
            {
                "name": "photo",
                "description": "Photo posts with images",
                "status": "enabled",
                "canDisable": True
            },
            {
                "name": "quote",
                "description": "Quote posts",
                "status": "enabled",
                "canDisable": True
            },
            {
                "name": "link",
                "description": "Link posts",
                "status": "disabled",
                "canDisable": True
            }
        ]
        
        for feather_data in sample_feathers:
            feather = Feather(**feather_data)
            db.add(feather)
        
        await db.commit()
        print("Sample data created successfully!")

if __name__ == "__main__":
    asyncio.run(create_sample_settings())
