#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🏗️  Starting build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable is not set"
    echo "Please set DATABASE_URL to your Supabase connection string"
    exit 1
fi

echo "✅ DATABASE_URL is configured"

# Run database migrations with Alembic
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Build completed successfully!"
