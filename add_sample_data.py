"""
Script to add sample data to the database for testing the new post types
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session, Base, engine
from app.crud import posts as post_crud, users as user_crud
from app.schemas import PostCreate, UserCreate
from app.models import Group, Category, Tag, Upload, Comment, Like, Share
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_sample_user():
    """Create a sample user for posts"""
    async with async_session() as db:
        # First, ensure we have a default group
        from sqlalchemy import select, insert
        
        # Check if group with id=1 exists, if not create one
        result = await db.execute(select(Group).filter(Group.id == 1))
        default_group = result.scalar_one_or_none()
        
        if not default_group:
            # Create default group
            default_group = Group(name="Default", id=1)
            db.add(default_group)
            await db.flush()
        
        # Check if user already exists
        user = await user_crud.get_user_by_email(db, "sample@example.com")
        if user:
            return user
        
        # Create sample user
        user_data = UserCreate(
            email="sample@example.com",
            username="sampleuser",
            password="samplepassword",
            full_name="Sample User",
            group_id=1  # Use the default group
        )
        user = await user_crud.create_user(db, user_data)
        await db.commit()
        return user

async def create_sample_categories(user_id: int):
    """Create sample categories"""
    async with async_session() as db:
        from sqlalchemy import select
        
        categories_data = [
            {"name": "Technology", "slug": "technology", "description": "Posts about technology and web development"},
            {"name": "Photography", "slug": "photography", "description": "Photo posts and visual content"},
            {"name": "Design", "slug": "design", "description": "Design-related posts and tutorials"},
            {"name": "Inspiration", "slug": "inspiration", "description": "Motivational and inspirational content"},
        ]
        
        created_categories = {}
        
        for cat_data in categories_data:
            # Check if category already exists
            result = await db.execute(
                select(Category).filter(Category.slug == cat_data["slug"])
            )
            existing_cat = result.scalar_one_or_none()
            
            if not existing_cat:
                category = Category(
                    user_id=user_id,
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"]
                )
                db.add(category)
                await db.flush()
                created_categories[cat_data["name"]] = category.id
            else:
                created_categories[cat_data["name"]] = existing_cat.id
        
        await db.commit()
        return created_categories

async def add_sample_posts():
    """Add sample posts with different content types"""
    user = await create_sample_user()
    categories = await create_sample_categories(user.id)
    
    sample_posts = [
        # Text Posts
        {
            "title": "The Future of Web Development in 2025",
            "type": "text",
            "body": "As we move into 2025, web development continues to evolve at a rapid pace. **AI-powered development tools** are becoming mainstream, **Edge computing** is changing how we think about performance, and **Web Components** are finally getting the adoption they deserve.\n\n### Key Trends to Watch:\n- Server-side rendering renaissance\n- Type-safe APIs everywhere\n- Progressive Web Apps going native\n\nWhat trends are you most excited about?",
            "tag_names": ["webdev", "future", "trends", "ai"],
            "category": "Technology",
            "status": "published",
            "url": "future-of-web-development-2025",
        },
        {
            "title": "My Journey Learning React",
            "type": "text",
            "body": "Six months ago, I started learning React coming from a vanilla JavaScript background. Here's what I wish I knew when I started:\n\n1. **Think in components** - Everything is a component\n2. **State management** - Start simple, add complexity when needed\n3. **Hooks are powerful** - They changed everything\n4. **Practice, practice, practice** - Build real projects\n\nThe learning curve was steep, but totally worth it!",
            "tag_names": ["react", "learning", "javascript", "beginner"],
            "category": "Technology",
            "status": "published",
            "url": "my-journey-learning-react",
        },
        {
            "title": "Why I Switched to TypeScript",
            "type": "text",
            "body": "After years of writing JavaScript, I finally made the switch to TypeScript. Here's why it was the best decision I made as a developer:\n\n✅ Catch errors at compile time\n✅ Better IDE support\n✅ Self-documenting code\n✅ Easier refactoring\n\nYes, there's a learning curve, but the productivity gains are incredible.",
            "tag_names": ["typescript", "javascript", "productivity"],
            "category": "Technology",
            "status": "published",
            "url": "why-i-switched-to-typescript",
        },
        
        # Photo Posts
        {
            "title": "Golden Hour Photography Tips",
            "type": "photo",
            "images": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=800&h=600&fit=crop",
            ],
            "caption": "The golden hour - that magical time right after sunrise and before sunset. Here are some shots I captured during my photography walk this weekend. The warm light makes everything look cinematic! 📸✨",
            "tag_names": ["photography", "goldenhour", "sunset", "tips"],
            "category": "Photography",
            "status": "published",
            "url": "golden-hour-photography-tips",
        },
        {
            "title": "Street Art Discovery in Downtown",
            "type": "photo",
            "images": [
                "https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=800&h=600&fit=crop",
            ],
            "caption": "Found some incredible street art during my downtown walk today. The creativity and colors are absolutely stunning! Each piece tells a story. 🎨 #StreetArt #UrbanExploration",
            "tag_names": ["streetart", "urban", "art", "downtown"],
            "category": "Photography",
            "status": "published",
            "url": "street-art-discovery-downtown",
        },
        {
            "title": "Morning Coffee Ritual",
            "type": "photo",
            "images": [
                "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&h=600&fit=crop",
            ],
            "caption": "There's something magical about that first cup of coffee in the morning. Today's brew: Ethiopian single origin with notes of blueberry and chocolate. Perfect start to the day! ☕",
            "tag_names": ["coffee", "morning", "ritual", "lifestyle"],
            "category": "Inspiration",
            "status": "published",
            "url": "morning-coffee-ritual",
        },
        
        # Video Posts
        {
            "title": "Building a REST API with FastAPI",
            "type": "video",
            "video_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
            "video_thumbnail": "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=800&h=450&fit=crop",
            "caption": "Complete tutorial on building a production-ready REST API using FastAPI. We'll cover authentication, database integration, and deployment. Perfect for beginners and intermediate developers!",
            "tag_names": ["fastapi", "python", "api", "tutorial"],
            "category": "Technology",
            "status": "published",
            "url": "building-rest-api-fastapi",
        },
        {
            "title": "React Hooks Explained in 10 Minutes",
            "type": "video",
            "video_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
            "video_thumbnail": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=450&fit=crop",
            "caption": "Quick and comprehensive guide to React Hooks. We'll cover useState, useEffect, useContext, and custom hooks with practical examples.",
            "tag_names": ["react", "hooks", "javascript", "tutorial"],
            "category": "Technology",
            "status": "published",
            "url": "react-hooks-explained",
        },
        
        # Audio Posts
        {
            "title": "The Tech Talk: AI and Ethics",
            "type": "audio",
            "audio_url": "https://sample-audio.com/tech-talk-ai-ethics.mp3",
            "duration": "23:45",
            "audio_description": "Deep dive discussion about the ethical implications of AI in software development. We explore bias in algorithms, privacy concerns, and the responsibility of developers in the AI age.",
            "tag_names": ["podcast", "ai", "ethics", "technology"],
            "category": "Technology",
            "status": "published",
            "url": "tech-talk-ai-ethics",
        },
        {
            "title": "Meditation and Mindfulness for Developers",
            "type": "audio",
            "audio_url": "https://sample-audio.com/meditation-developers.mp3",
            "duration": "18:30",
            "audio_description": "A guided meditation session specifically designed for developers. Learn techniques to manage stress, improve focus, and maintain work-life balance in the fast-paced tech industry.",
            "tag_names": ["meditation", "wellness", "developers", "mindfulness"],
            "category": "Inspiration",
            "status": "published",
            "url": "meditation-mindfulness-developers",
        },
        
        # Quote Posts
        {
            "title": "On Innovation and Creativity",
            "type": "quote",
            "quote": "Innovation is not about saying yes to everything. It's about saying no to all but the most crucial features.",
            "quote_source": "Steve Jobs",
            "tag_names": ["innovation", "creativity", "product", "design"],
            "category": "Inspiration",
            "status": "published",
            "url": "on-innovation-creativity",
        },
        {
            "title": "The Power of Simplicity",
            "type": "quote",
            "quote": "Simplicity is the ultimate sophistication. When you can't make it simpler, you've reached perfection.",
            "quote_source": "Leonardo da Vinci",
            "tag_names": ["simplicity", "design", "philosophy", "perfection"],
            "category": "Design",
            "status": "published",
            "url": "power-of-simplicity",
        },
        {
            "title": "On Continuous Learning",
            "type": "quote",
            "quote": "The beautiful thing about learning is that no one can take it away from you. In our industry, continuous learning isn't optional—it's survival.",
            "quote_source": "B.B. King (adapted for tech)",
            "tag_names": ["learning", "growth", "education", "career"],
            "category": "Inspiration",
            "status": "published",
            "url": "on-continuous-learning",
        },
        
        # Link Posts
        {
            "title": "The State of JavaScript 2024 Survey Results",
            "type": "link",
            "link_url": "https://stateofjs.com/2024/",
            "link_title": "State of JavaScript 2024: What Developers Really Think",
            "link_description": "Comprehensive survey results covering the most popular frameworks, libraries, and tools in the JavaScript ecosystem. React continues to dominate, but Vue and Svelte are gaining ground.",
            "link_thumbnail": "https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=800&h=400&fit=crop",
            "tag_names": ["javascript", "survey", "frameworks", "trends"],
            "category": "Technology",
            "status": "published",
            "url": "state-of-javascript-2024",
        },
        {
            "title": "Amazing CSS Grid Layout Examples",
            "type": "link",
            "link_url": "https://cssgrid-generator.netlify.app/",
            "link_title": "CSS Grid Generator - Interactive Grid Layout Tool",
            "link_description": "Fantastic tool for creating CSS Grid layouts visually. Perfect for designers and developers who want to master CSS Grid without memorizing all the property names.",
            "link_thumbnail": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=400&fit=crop",
            "tag_names": ["css", "grid", "layout", "tools"],
            "category": "Design",
            "status": "published",
            "url": "css-grid-layout-examples",
        },
        {
            "title": "Free Design Resources Every Developer Needs",
            "type": "link",
            "link_url": "https://github.com/bradtraversy/design-resources-for-developers",
            "link_title": "Design Resources for Developers - Curated List",
            "link_description": "Massive collection of free design and UI resources including color palettes, fonts, icons, illustrations, and stock photos. Bookmark this for your next project!",
            "link_thumbnail": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=400&fit=crop",
            "tag_names": ["design", "resources", "free", "ui"],
            "category": "Design",
            "status": "published",
            "url": "free-design-resources-developers",
        },
        
        # More diverse content
        {
            "title": "Remote Work Setup That Changed My Life",
            "type": "text",
            "body": "After two years of working from home, I finally found the perfect setup. Here's what made the biggest difference:\n\n🖥️ **Dual monitor setup** - Game changer for productivity\n💺 **Ergonomic chair** - Your back will thank you\n🎧 **Noise-canceling headphones** - Essential for focus\n💡 **Good lighting** - LED desk lamp with adjustable temperature\n\nInvestment in your workspace is investment in your career!",
            "tag_names": ["remote", "workspace", "productivity", "wfh"],
            "category": "Inspiration",
            "status": "published",
            "url": "remote-work-setup",
        },
        {
            "title": "Nature Photography from My Hiking Trip",
            "type": "photo",
            "images": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800&h=600&fit=crop",
            ],
            "caption": "Spent the weekend hiking in the mountains and captured some incredible landscapes. There's nothing like disconnecting from code and connecting with nature to reset your mind and creativity. 🏔️🌲",
            "tag_names": ["nature", "hiking", "landscape", "photography"],
            "category": "Photography",
            "status": "published",
            "url": "nature-photography-hiking-trip",
        },
        {
            "title": "Debugging Strategies for Complex Applications",
            "type": "text",
            "body": "Debugging complex applications can be frustrating. Here are strategies that have saved me countless hours:\n\n1. **Reproduce the bug consistently** - If you can't reproduce it, you can't fix it\n2. **Use proper logging** - Console.log is your friend, but use it wisely\n3. **Isolate the problem** - Binary search approach\n4. **Check the obvious first** - Is the server running? Are you connected?\n5. **Read error messages carefully** - They're usually more helpful than you think\n\nRemember: Every bug is an opportunity to understand your code better!",
            "tag_names": ["debugging", "tips", "programming", "problem-solving"],
            "category": "Technology",
            "status": "published",
            "url": "debugging-strategies-complex-applications",
        },
        {
            "title": "Building My First Mobile App",
            "type": "video",
            "video_url": "https://sample-videos.com/mobile-app-development.mp4",
            "video_thumbnail": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=800&h=450&fit=crop",
            "caption": "Follow along as I build my first mobile app using React Native. We'll go from idea to app store submission, covering UI design, state management, and deployment.",
            "tag_names": ["mobile", "react-native", "app", "development"],
            "category": "Technology",
            "status": "published",
            "url": "building-first-mobile-app",
        }
    ]
    
    async with async_session() as db:
        for post_data in sample_posts:
            # Map category name to ID
            category_name = post_data.pop('category', None)
            if category_name and category_name in categories:
                # Note: The current schema might not have category_id, 
                # but we'll store it in the category field as a string for now
                post_data['category'] = category_name
            
            # Remove user_id from post_data if it exists
            post_data.pop('user_id', None)
            
            # Extract media files for uploads
            images = post_data.pop('images', [])
            video_url = post_data.get('video_url')
            audio_url = post_data.get('audio_url')
            
            # Create the post
            try:
                post_create = PostCreate(**post_data)
                created_post = await post_crud.create_post(db, post_create, user.id)
                print(f"Created post: {created_post.title} (ID: {created_post.id})")
                
                # Create uploads for images
                if images:
                    for idx, image_url in enumerate(images):
                        upload = Upload(
                            url=image_url,
                            user_id=user.id,
                            post_id=created_post.id,
                            type="image",
                            size=1024000,  # Mock size
                            name=f"image_{idx + 1}.jpg",
                            alternative_text=f"Image {idx + 1} for {created_post.title}",
                            source="unsplash",
                            mime_type="image/jpeg"
                        )
                        db.add(upload)
                
                # Create upload for video
                if video_url:
                    upload = Upload(
                        url=video_url,
                        user_id=user.id,
                        post_id=created_post.id,
                        type="video",
                        size=2048000,  # Mock size
                        name="sample_video.mp4",
                        alternative_text=f"Video for {created_post.title}",
                        source="sample-videos",
                        mime_type="video/mp4"
                    )
                    db.add(upload)
                
                # Create upload for audio
                if audio_url:
                    upload = Upload(
                        url=audio_url,
                        user_id=user.id,
                        post_id=created_post.id,
                        type="audio",
                        size=512000,  # Mock size
                        name="sample_audio.mp3",
                        alternative_text=f"Audio for {created_post.title}",
                        source="sample-audio",
                        mime_type="audio/mpeg"
                    )
                    db.add(upload)
                
                await db.commit()
                
                # Add some sample interactions (comments, likes, shares)
                await add_sample_interactions(db, created_post.id, user.id)
                
            except Exception as e:
                print(f"Error creating post '{post_data.get('title', 'Unknown')}': {e}")
                await db.rollback()
                continue

async def add_sample_interactions(db: AsyncSession, post_id: int, user_id: int):
    """Add sample comments, likes, and shares to posts"""
    import random
    
    # Add some comments
    sample_comments = [
        "Great post! Thanks for sharing.",
        "Very informative, learned something new today.",
        "Love this content, keep it up!",
        "Interesting perspective on this topic.",
        "Thanks for the detailed explanation."
    ]
    
    # Add 1-3 random comments
    num_comments = random.randint(1, 3)
    for i in range(num_comments):
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            body=random.choice(sample_comments),
            status="approved"
        )
        db.add(comment)
    
    # Add a like from the post author (only one per post)
    try:
        like = Like(
            post_id=post_id,
            user_id=user_id
        )
        db.add(like)
    except Exception:
        # Like might already exist, skip
        pass
    
    # Add some shares (random number between 1-3)
    num_shares = random.randint(1, 3)
    platforms = ["twitter", "facebook", "linkedin", "reddit"]
    for i in range(num_shares):
        share = Share(
            post_id=post_id,
            user_id=user_id,
            platform=random.choice(platforms)
        )
        db.add(share)
    
    await db.commit()

async def main():
    """Main function to run the data seeding"""
    print("Initializing database...")
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Adding sample posts...")
    await add_sample_posts()
    
    print("Sample data added successfully!")

if __name__ == "__main__":
    asyncio.run(main())
