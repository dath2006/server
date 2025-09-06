#!/usr/bin/env bash
# Development setup script
set -o errexit

echo "Setting up development environment..."

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Check Python version
python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $python_version"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your actual configuration values"
else
    echo "✅ .env file already exists"
fi

# Check if PostgreSQL is accessible
echo "🔍 Checking database connection..."
if python -c "
import asyncio
import sys
try:
    from app.database import engine
    from sqlalchemy import text
    
    async def check_db():
        try:
            async with engine.begin() as conn:
                await conn.execute(text('SELECT 1'))
            return True
        except Exception as e:
            print(f'Database connection error: {e}')
            return False
    
    result = asyncio.run(check_db())
    if not result:
        sys.exit(1)
except Exception as e:
    print(f'Configuration error: {e}')
    sys.exit(1)
" 2>/dev/null; then
    echo "✅ Database connection successful"
    
    # Run database migrations
    echo "🔄 Running database migrations..."
    alembic upgrade head
    
    # Optionally add sample data
    if [ "$1" == "--with-sample-data" ]; then
        echo "📊 Adding sample data..."
        python add_sample_data.py
        echo "✅ Sample data added"
    fi
else
    echo "❌ Database connection failed. Please:"
    echo "   1. Make sure PostgreSQL is running"
    echo "   2. Check your DATABASE_URL in .env file"
    echo "   3. Create the database if it doesn't exist"
fi

# Create uploads directory structure (fallback storage)
echo "📁 Setting up local storage directories..."
mkdir -p uploads/images uploads/videos uploads/audios uploads/files uploads/avatars uploads/captions

echo ""
echo "🎉 Development setup completed!"
echo ""
echo "🚀 To start the server:"
echo "   python run.py"
echo ""
echo "📚 To add sample data (if not done already):"
echo "   python add_sample_data.py"
echo ""
echo "☁️  Cloudinary integration:"
echo "   - Configure CLOUDINARY_* variables in .env for cloud storage"
echo "   - Files will fallback to local /uploads directory if Cloudinary is not configured"
