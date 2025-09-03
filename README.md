# Chryp Lite Reimagined - FastAPI Backend

A modern FastAPI backend with SQLAlchemy 2.0 and PostgreSQL for the Chryp Lite CMS redesign project.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy 2.0**: Latest version with async support
- **PostgreSQL**: Robust relational database
- **Alembic**: Database migration management
- **JWT Authentication**: Secure token-based authentication
- **CORS Support**: Ready for Next.js frontend integration
- **Pydantic**: Data validation and serialization

## Project Structure

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication utilities
│   ├── crud/                # CRUD operations
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── posts.py
│   └── routers/             # API routes
│       ├── __init__.py
│       ├── auth.py
│       ├── users.py
│       └── posts.py
├── alembic/                 # Database migrations
├── alembic.ini             # Alembic configuration
├── requirements.txt        # Python dependencies
├── run.py                  # Development server
└── .env.example           # Environment variables template
```

## Setup Instructions

### 1. Environment Setup

Create a virtual environment and activate it:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

1. Install and start PostgreSQL
2. Create a database named `chyrp_lite`
3. Copy `.env.example` to `.env` and update the database credentials:

```bash
cp .env.example .env
```

Update the `.env` file with your database credentials:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/chyrp_lite
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
```

### 4. Database Migration

Initialize and run the first migration:

```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 5. Run the Application

For development:

```bash
# Using the run script
python run.py

# Or directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

- **Main API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Login and get access token
- `GET /api/v1/auth/me` - Get current user info

### Users

- `GET /api/v1/users/` - Get list of users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `POST /api/v1/users/` - Create new user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

### Posts

- `GET /api/v1/posts/` - Get list of posts
- `GET /api/v1/posts/pinned` - Get pinned posts
- `GET /api/v1/posts/{post_id}` - Get post by ID
- `POST /api/v1/posts/` - Create new post
- `PUT /api/v1/posts/{post_id}` - Update post
- `DELETE /api/v1/posts/{post_id}` - Delete post

## Database Models

The following models are implemented based on your Prisma schema:

- **Users**: User accounts and authentication
- **Posts**: Blog posts and content
- **Pages**: Static pages
- **Comments**: Post comments
- **Categories**: Content categorization
- **Groups**: User groups and permissions
- **Likes**: Post likes/reactions
- **Views**: Post view tracking
- **Sessions**: User sessions
- **Permissions**: Role-based permissions
- **Pingbacks**: External link tracking
- **PostAttributes**: Additional post metadata

## Development

### Adding New Endpoints

1. Create CRUD operations in `app/crud/`
2. Add Pydantic schemas in `app/schemas.py`
3. Create API routes in `app/routers/`
4. Include the router in `app/main.py`

### Database Changes

When modifying models:

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head
```

### Testing

The API includes interactive documentation at `/docs` where you can test all endpoints.

## Production Deployment

1. Set secure environment variables
2. Use a proper WSGI server like Gunicorn
3. Configure SSL/TLS
4. Set up proper logging
5. Use environment-specific configurations

## Next Steps

- Add more CRUD operations for remaining models
- Implement role-based permissions
- Add file upload capabilities
- Create comprehensive test suite
- Add API rate limiting
- Implement caching strategies
