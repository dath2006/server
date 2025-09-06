#!/usr/bin/env bash
# Production deployment script
set -o errexit

echo "Starting deployment..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if database is accessible
echo "Checking database connection..."
python -c "
import asyncio
from app.database import engine
from sqlalchemy import text

async def check_db():
    try:
        async with engine.begin() as conn:
            await conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

result = asyncio.run(check_db())
if not result:
    exit(1)
"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Check if migrations were successful
echo "Verifying migrations..."
python -c "
import asyncio
from app.database import engine
from sqlalchemy import text

async def check_migrations():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT version_num FROM alembic_version'))
            version = result.scalar()
            print(f'✅ Current database version: {version}')
    except Exception as e:
        print(f'❌ Migration verification failed: {e}')
        exit(1)

asyncio.run(check_migrations())
"

# Create uploads directory structure if it doesn't exist (fallback storage)
echo "Setting up local storage directories..."
mkdir -p uploads/images uploads/videos uploads/audios uploads/files uploads/avatars uploads/captions

echo "✅ Deployment completed successfully!"
echo "📁 Local storage fallback directories created"
echo "☁️  Cloudinary will be used if configured, otherwise files will be stored locally"
