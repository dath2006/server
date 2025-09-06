#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations with Alembic
echo "Running database migrations..."
alembic upgrade head

echo "Build completed successfully!"
