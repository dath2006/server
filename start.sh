#!/usr/bin/env bash

echo "🚀 Starting FastAPI application..."

# Check if required environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable is not set"
    exit 1
fi

# Create uploads directory structure (fallback storage)
mkdir -p uploads/images uploads/videos uploads/audios uploads/files uploads/avatars uploads/captions

# Start the FastAPI application with Uvicorn
# Use 0.0.0.0 to bind to all interfaces (required for Render)
# Use PORT environment variable provided by Render
echo "🌐 Starting server on port ${PORT:-8000}..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
