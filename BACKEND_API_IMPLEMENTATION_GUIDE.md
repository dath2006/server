# Backend API Implementation Guide

This document outlines all the API routes that have been implemented in the frontend and what the backend needs to handle.

## API Base Configuration

- **Base URL**: `/api/v1`
- **Authentication**: Bearer token (passed via Authorization header)
- **Content-Type**: `application/json`

## 1. Comments API (`/api/v1/admin/comments`)

### GET `/api/v1/admin/comments`

**Purpose**: Fetch paginated list of comments with filtering

**Query Parameters**:

```typescript
{
  page?: number;           // Default: 1
  limit?: number;          // Default: 20
  status?: 'pending' | 'approved' | 'spam' | 'denied';
  search?: string;         // Search in comment body and author name
  author?: string;         // Filter by author
  post_id?: string;        // Filter by specific post
  date_from?: string;      // ISO date string
  date_to?: string;        // ISO date string
  sort?: 'created_at' | 'updated_at';
  order?: 'asc' | 'desc';  // Default: 'desc'
}
```

**Response Format**:

```typescript
{
  data: Comment[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
  stats: {
    total: number;
    pending: number;
    approved: number;
    spam: number;
    denied: number;
  };
}
```

**Comment Object Structure**:

```typescript
{
  id: string;
  body: string;
  author: string;
  email: string;
  url?: string;
  ip: string;
  status: 'pending' | 'approved' | 'spam' | 'denied';
  created_at: string;      // ISO date string
  updated_at: string;      // ISO date string
  post: {
    id: string;
    title: string;
    url: string;
  };
}
```

### PUT `/api/v1/admin/comments/{id}/status`

**Purpose**: Update comment status

**Request Body**:

```typescript
{
  status: "pending" | "approved" | "spam" | "denied";
}
```

**Response**: Updated comment object

### DELETE `/api/v1/admin/comments/{id}`

**Purpose**: Delete a comment

**Response**:

```typescript
{
  success: boolean;
  message: string;
}
```

### POST `/api/v1/admin/comments/batch`

**Purpose**: Perform batch actions on multiple comments

**Request Body**:

```typescript
{
  commentIds: string[];
  action: 'approve' | 'deny' | 'spam' | 'delete';
}
```

**Response**:

```typescript
{
  success: boolean;
  processed: number;
  errors?: Array<{
    commentId: string;
    error: string;
  }>;
}
```

## 2. Spam API (`/api/v1/admin/spam`)

### GET `/api/v1/admin/spam`

**Purpose**: Fetch paginated list of spam items

**Query Parameters**:

```typescript
{
  page?: number;           // Default: 1
  limit?: number;          // Default: 20
  status?: 'spam' | 'approved' | 'rejected';
  search?: string;         // Search in content and author
  date_from?: string;      // ISO date string
  date_to?: string;        // ISO date string
  sort?: 'created_at' | 'updated_at';
  order?: 'asc' | 'desc';  // Default: 'desc'
}
```

**Response Format**:

```typescript
{
  data: SpamItem[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
  stats: {
    total: number;
    spam: number;
    approved: number;
    rejected: number;
  };
}
```

**SpamItem Object Structure**:

```typescript
{
  id: string;
  content: string;
  author: string;
  email: string;
  ip: string;
  status: 'spam' | 'approved' | 'rejected';
  created_at: string;      // ISO date string
  updated_at: string;      // ISO date string
  post?: {                 // Optional, if related to a post
    id: string;
    title: string;
    url: string;
  };
}
```

### PUT `/api/v1/admin/spam/{id}/status`

**Purpose**: Update spam item status

**Request Body**:

```typescript
{
  status: "spam" | "approved" | "rejected";
}
```

**Response**: Updated spam item object

### DELETE `/api/v1/admin/spam/{id}`

**Purpose**: Delete a spam item

**Response**:

```typescript
{
  success: boolean;
  message: string;
}
```

### POST `/api/v1/admin/spam/batch`

**Purpose**: Perform batch actions on multiple spam items

**Request Body**:

```typescript
{
  spamIds: string[];
  action: 'approve' | 'reject' | 'delete';
}
```

**Response**:

```typescript
{
  success: boolean;
  processed: number;
  errors?: Array<{
    spamId: string;
    error: string;
  }>;
}
```

### POST `/api/v1/admin/spam/mark-comment`

**Purpose**: Mark a specific comment as spam

**Request Body**:

```typescript
{
  commentId: string;
}
```

**Response**: New spam item object

### GET `/api/v1/admin/spam/stats`

**Purpose**: Get spam statistics

**Response**:

```typescript
{
  total: number;
  spam: number;
  approved: number;
  rejected: number;
}
```

## Error Handling

All endpoints should return consistent error responses:

```typescript
{
  error: {
    code: string;          // Error code (e.g., 'COMMENT_NOT_FOUND')
    message: string;       // Human-readable error message
    details?: any;         // Additional error details
  };
  status: number;          // HTTP status code
}
```

## Common HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Unprocessable Entity (business logic errors)
- `500`: Internal Server Error

## Authentication

All admin endpoints require authentication. The frontend sends the bearer token in the Authorization header:

```
Authorization: Bearer <token>
```

## Database Considerations

### Comments Table Fields

- `id` (primary key)
- `body` (text)
- `author` (varchar)
- `email` (varchar)
- `url` (varchar, nullable)
- `ip` (varchar)
- `status` (enum: pending, approved, spam, denied)
- `post_id` (foreign key)
- `created_at` (timestamp)
- `updated_at` (timestamp)

## Frontend Implementation

The frontend has been fully implemented with:

1. **API Modules**:

   - `lib/api/admin-comments.ts` - Complete comments API integration
   - `lib/api/admin-spam.ts` - Complete spam API integration

2. **React Hooks**:

   - `hooks/useComments.ts` - State management for comments
   - `hooks/useSpam.ts` - State management for spam

3. **UI Components**:

   - `components/admin/comments/CommentsPage.tsx` - Enhanced UI
   - `components/admin/spam/SpamPage.tsx` - Simplified UI
   - All supporting components (cards, modals, etc.)

4. **Features Implemented**:
   - Pagination
   - Filtering and search
   - Batch operations
   - Status management
   - Error handling
   - Loading states
   - Real-time stats updates

## Next Steps for Backend

1. Implement all the API endpoints as specified above
2. Set up proper database schema with indexes for performance
3. Implement authentication middleware
4. Add input validation using the provided TypeScript interfaces
5. Set up proper error handling and logging
6. Consider rate limiting for admin endpoints
7. Test all endpoints with the frontend implementation

The frontend is ready to integrate once the backend APIs are implemented according to this specification.
