# API Request Format Changes - Post Creation

## Overview

Updated the frontend API client to match the documented multipart/form-data approach for posts containing files, while maintaining JSON format for text-only posts.

## Request Formats

### 1. Text-Only Posts (JSON)

**Post Types**: `text`, `quote`, `link` (without files)

```http
POST /api/v1/admin/posts
Content-Type: application/json

{
  "title": "My Text Post",
  "type": "text",
  "content": {
    "body": "**Markdown** content here"
  },
  "status": "published",
  "tags": ["sample"],
  "category": "general"
}
```

### 2. Posts with Files (Multipart)

**Post Types**: `photo`, `video`, `audio`, `file`

```http
POST /api/v1/admin/posts
Content-Type: multipart/form-data

data: '{"title": "My Photo Post", "type": "photo", "status": "published", "tags": ["vacation"], "category": "travel", "content": {"caption": "Beautiful sunset", "altText": "Sunset over mountains"}}'
imageFiles_0: [binary image data]
imageFiles_1: [binary image data]
```

## Backend Processing Expected

### 1. Detect Request Type

```python
@app.post("/api/v1/admin/posts")
async def create_post(request: Request):
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # Handle multipart with files
        form = await request.form()
        data = json.loads(form.get("data"))
        files = extract_files_from_form(form)
        return await create_post_with_files(data, files)
    else:
        # Handle JSON
        data = await request.json()
        return await create_post_json(data)
```

### 2. File Field Mapping

| Frontend Field           | Form Field Pattern                      | Description              |
| ------------------------ | --------------------------------------- | ------------------------ |
| `content.imageFiles[]`   | `imageFiles_0`, `imageFiles_1`, ...     | Photo post images        |
| `content.videoFile`      | `videoFile`                             | Video file upload        |
| `content.posterImage`    | `posterImage`                           | Video thumbnail          |
| `content.captionFiles[]` | `captionFiles_0`, `captionFiles_1`, ... | Video subtitles          |
| `content.audioFile`      | `audioFile`                             | Audio file upload        |
| `content.captionFile`    | `captionFile`                           | Audio transcript         |
| `content.files[]`        | `files_0`, `files_1`, ...               | General file attachments |

### 3. Database Mapping

The `data` JSON field contains:

```json
{
  "title": "Post Title",
  "type": "photo",
  "status": "published",
  "tags": ["tag1", "tag2"],
  "category": "general",
  "content": {
    "caption": "Photo caption",
    "altText": "Alt text",
    "description": "Description"
    // ... other non-file fields
  }
}
```

**Map to database as:**

```python
# posts table
posts_data = {
    "title": data["title"],
    "type": data["type"],
    "status": data["status"],
    "url": generate_url_from_title(data["title"]),
    "category_id": get_or_create_category(data["category"]),
    # Content fields based on type
    "body": data["content"].get("body"),  # text posts
    "caption": data["content"].get("caption"),  # photo posts
    "description": data["content"].get("description"),  # video/audio/file posts
}

# post_attributes table
attributes_data = {
    "alt_text": data["content"].get("altText"),
    "source_url": data["content"].get("sourceUrl"),
    # ... other type-specific attributes
}
```

## Changes Made to Frontend

### 1. Enhanced CreatePostData Interface

```typescript
export interface CreatePostData {
  title: string;
  type: PostType;
  content: PostContent;
  status: PostStatus;
  tags: string[];
  category: string;
  slug?: string; // NEW
  isPinned?: boolean; // NEW
  allowComments?: boolean; // NEW
  scheduledDate?: string; // NEW
  visibility?: string; // NEW
  visibilityGroups?: string[]; // NEW
}
```

### 2. Smart Request Handling

```typescript
// Automatically detects if files are present
const hasFiles = this.postHasFiles(postData);

if (hasFiles) {
  // Send as multipart/form-data
  const formData = this.createFormData(postData);
  // ...
} else {
  // Send as JSON
  // ...
}
```

### 3. File Detection Logic

```typescript
postHasFiles(postData: CreatePostData): boolean {
  const { type, content } = postData;

  switch (type) {
    case "photo": return !!(content as any).imageFiles?.length;
    case "video": return !!(content as any).videoFile || /* ... */;
    case "audio": return !!(content as any).audioFile || /* ... */;
    case "file": return !!(content as any).files?.length;
    default: return false;
  }
}
```

### 4. FormData Creation

- Separates file content from JSON metadata
- Creates indexed field names for arrays (`imageFiles_0`, `imageFiles_1`)
- Preserves non-file content in the `data` JSON field

## Example Requests

### Text Post (JSON)

```json
{
  "title": "How to Train a Dragon",
  "type": "text",
  "content": {
    "body": "**Be the one who trains the dragon**\n\n# Be yourself and be splendid\n- Point 1\n- Point 2"
  },
  "status": "published",
  "tags": ["tutorial", "dragons"],
  "category": "guides"
}
```

### Photo Post (Multipart)

```
data: '{"title": "Vacation Photos", "type": "photo", "status": "published", "tags": ["vacation"], "category": "travel", "content": {"caption": "Amazing sunset views!", "altText": "Sunset over mountains"}}'
imageFiles_0: [sunset1.jpg binary data]
imageFiles_1: [sunset2.jpg binary data]
```

### Video Post (Multipart)

```
data: '{"title": "Tutorial Video", "type": "video", "status": "published", "content": {"sourceType": "upload", "description": "Learn the basics"}}'
videoFile: [tutorial.mp4 binary data]
posterImage: [thumbnail.jpg binary data]
captionFiles_0: [subtitles-en.vtt binary data]
```

## Backward Compatibility

The API client maintains backward compatibility:

- Text posts continue using JSON (no breaking changes)
- File posts now use multipart (new functionality)
- All existing text post creation continues to work
