@echo off
echo Setting up Chryp Lite FastAPI Backend...
echo.

echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, removing old one...
    rmdir /s /q venv
)
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    echo Try running: pip install --no-cache-dir -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Setup complete!
echo.
echo To activate the environment in the future, run:
echo   venv\Scripts\activate
echo.
echo To start the development server, run:
echo   python run.py
echo.
echo Don't forget to:
echo 1. Copy .env.example to .env
echo 2. Update database credentials in .env
echo 3. Create PostgreSQL database
echo 4. Run: alembic revision --autogenerate -m "Initial migration"
echo 5. Run: alembic upgrade head
echo 6. Run: python init_db.py (to create admin user)

pause
