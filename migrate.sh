#!/usr/bin/env bash
# Migration script with retry logic for deployment environments

set -o errexit

echo "🔄 Starting database migration..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable is not set"
    exit 1
fi

# Function to test database connection
test_db_connection() {
    python3 -c "
import asyncio
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def test_connection():
    try:
        # Use sync engine for quick connection test
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print('❌ DATABASE_URL not found')
            return False
            
        # Handle both postgres:// and postgresql:// schemes
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
        engine = create_engine(database_url)
        with engine.begin() as conn:
            conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
        return True
    except OperationalError as e:
        print(f'❌ Database connection failed: {e}')
        return False
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        return False

if not test_connection():
    sys.exit(1)
"
}

# Retry logic for database connection
echo "🔍 Testing database connection..."
max_retries=5
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if test_db_connection; then
        break
    else
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            echo "⏳ Retrying in 10 seconds... (Attempt $retry_count/$max_retries)"
            sleep 10
        else
            echo "❌ Failed to connect to database after $max_retries attempts"
            echo "Please check your DATABASE_URL and ensure the database is accessible"
            exit 1
        fi
    fi
done

# Run migrations
echo "🚀 Running Alembic migrations..."
alembic upgrade head

echo "✅ Database migration completed successfully!"
