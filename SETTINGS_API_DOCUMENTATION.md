# Backend API Documentation: `/api/v1/settings`

## Overview

The `/api/v1/settings` endpoint provides global site configuration data by combining information from multiple database tables: `settings`, `themes`, `modules`, and `feathers`. The endpoint handles both authenticated and non-authenticated requests, returning different levels of data based on user permissions.

## Database Tables Used

### 1. `settings` Table

Stores key-value configuration pairs with type information:

```sql
- id (Primary Key)
- name (Unique setting name)
- value (Setting value as text)
- description (Optional description)
- type (string, boolean, number, json)
- created_at, updated_at
```

### 2. `themes` Table

Stores available themes:

```sql
- id (Primary Key)
- name (Theme name)
- description (Theme description)
- isActive (Boolean - which theme is currently active)
```

### 3. `modules` Table

Stores installed modules/plugins:

```sql
- id (Primary Key)
- name (Module name)
- description (Module description)
- status (enabled/disabled)
- canDisable (Boolean)
- canUninstall (Boolean)
- conflicts (Text - conflicting modules)
```

### 4. `feathers` Table

Stores post types (feathers):

```sql
- id (Primary Key)
- name (Feather name)
- description (Feather description)
- status (enabled/disabled)
- canDisable (Boolean)
```

## API Endpoints

### GET `/api/v1/settings`

**Authentication:** Optional

- **Public Access:** Returns public settings and non-sensitive data
- **Admin Access:** Returns all settings including sensitive data

**Request Headers:**

```http
# Optional - if user is authenticated
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response Format:**

```json
{
  // Basic site settings (always returned)
  "site_title": "My Awesome Blog",
  "site_description": "A blog about awesome things",
  "site_url": "https://myblog.com",
  "timezone": "UTC",
  "locale": "en",

  // Content settings (always returned)
  "posts_per_page": 10,
  "enable_registration": true,
  "enable_comments": true,
  "enable_trackbacks": false,
  "enable_webmentions": true,
  "enable_feeds": true,
  "enable_search": true,
  "maintenance_mode": false,

  // Current active theme (always returned)
  "theme": "default",

  // Social media links (always returned)
  "social_links": {
    "facebook": "https://facebook.com/myblog",
    "twitter": "https://twitter.com/myblog",
    "instagram": "https://instagram.com/myblog",
    "linkedin": "",
    "github": "https://github.com/myblog"
  },

  // SEO settings (always returned)
  "seo_settings": {
    "meta_description": "Default meta description",
    "meta_keywords": "blog, awesome, content",
    "og_image": "https://myblog.com/og-image.jpg"
  },

  // Admin-only settings (only returned for authenticated admin users)
  "admin_email": "admin@myblog.com",
  "smtp_settings": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "user@gmail.com",
    "password": "encrypted_password",
    "encryption": "tls"
  },

  // Module information (always returned)
  "modules": [
    {
      "id": 1,
      "name": "comments",
      "description": "Comment system module",
      "status": "enabled",
      "can_disable": true,
      "can_uninstall": false,
      "conflicts": null
    }
  ],

  // Theme information (always returned)
  "themes": [
    {
      "id": 1,
      "name": "default",
      "description": "Default theme",
      "is_active": true
    },
    {
      "id": 2,
      "name": "dark",
      "description": "Dark theme",
      "is_active": false
    }
  ],

  // Post type (feather) information (always returned)
  "feathers": [
    {
      "id": 1,
      "name": "text",
      "description": "Basic text posts",
      "status": "enabled",
      "can_disable": false
    },
    {
      "id": 2,
      "name": "photo",
      "description": "Photo posts with images",
      "status": "enabled",
      "can_disable": true
    }
  ]
}
```

### PUT `/api/v1/settings`

**Authentication:** Required (Admin only)
**Description:** Updates site settings

**Request Headers:**

```http
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "site_title": "Updated Site Title",
  "posts_per_page": 15,
  "maintenance_mode": true,
  "social_links": {
    "facebook": "https://facebook.com/newpage",
    "twitter": "https://twitter.com/newhandle"
  }
}
```

**Response:** Returns the updated settings in the same format as GET request.

## Data Type Conversion

The backend automatically converts database string values to appropriate types:

- **Boolean Settings:** `"true"`, `"1"`, `"yes"`, `"on"` → `true`; others → `false`
- **Number Settings:** Converts to `int` or `float` as appropriate
- **JSON Settings:** Parses JSON strings into objects
- **String Settings:** Returns as-is

## Security and Access Control

### Public Settings (No Authentication Required)

- Basic site information
- Content display settings
- Theme and module information
- Non-sensitive configuration

### Admin-Only Settings (Authentication Required)

The following settings are filtered out for non-admin users:

- `admin_email`
- `smtp_*` settings
- `database_url`
- `secret_key`
- `jwt_secret`
- `google_client_*`
- `api_keys`

### User Roles

Based on the `group_id` in the users table:

- `group_id: 1` → `"admin"` (full access)
- `group_id: 2` → `"editor"` (public settings only)
- `group_id: 3` → `"author"` (public settings only)
- `group_id: 4` → `"member"` (public settings only)
- `group_id: 5` → `"user"` (public settings only)

## Error Responses

### 500 Internal Server Error

```json
{
  "detail": "Error fetching settings: <error_message>"
}
```

### 401 Unauthorized (PUT only)

```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden (PUT only)

```json
{
  "detail": "Admin access required"
}
```

## Frontend Integration

The frontend Redux store expects this exact response format. Key points:

1. **Direct Object Response:** No wrapper objects like `{success: true, data: {...}}`
2. **Proper Type Conversion:** Booleans as actual booleans, numbers as numbers
3. **Consistent Structure:** All fields are optional with sensible defaults
4. **Nested Objects:** Complex settings like `social_links` and `seo_settings` as nested objects

## Sample Data Setup

To populate the database with sample data for testing:

```bash
cd server
python create_sample_settings.py
```

This will create:

- Basic site settings
- Sample themes (default, dark, minimal)
- Sample modules (comments, search, feeds)
- Sample feathers (text, photo, quote, link)

## Example Usage

### Frontend (Redux)

```typescript
// Automatic fetch on app load
const settings = useAppSelector(selectSettingsData);
const siteTitle = useAppSelector(selectSiteTitle);
const enableComments = useAppSelector(selectEnableComments);
```

### Manual API Call

```bash
# Public access
curl http://localhost:8000/api/v1/settings

# Admin access
curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8000/api/v1/settings

# Update settings
curl -X PUT \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"site_title": "New Title", "maintenance_mode": true}' \
     http://localhost:8000/api/v1/settings
```
