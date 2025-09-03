from typing import Dict, List, Optional, Any
from app.models import Post, User, Comment
from app.schemas import PostResponse, CommentResponse, UserResponse, PostContent


def format_post_for_api(post: Post) -> Dict[str, Any]:
    """
    Format a post database model into the TypeScript interface format
    """
    # Format user/author
    user_data = None
    if post.user:
        user_data = {
            "id": str(post.user.id),
            "email": post.user.email,
            "username": post.user.username,
            "full_name": post.user.full_name,
            "website": post.user.website,
            "image": post.user.image,
            "joined_at": post.user.joined_at
        }

    # Format content based on post type
    content = {}
    
    if post.type == "text":
        content = {"body": post.body}
    elif post.type == "photo":
        content = {
            "images": post.images or [],
            "caption": post.caption
        }
    elif post.type == "video":
        content = {
            "videoUrl": post.video_url,
            "videoThumbnail": post.video_thumbnail
        }
    elif post.type == "audio":
        content = {
            "audioUrl": post.audio_url,
            "duration": post.duration,
            "audioDescription": post.audio_description
        }
    elif post.type == "quote":
        content = {
            "quote": post.quote,
            "source": post.quote_source
        }
    elif post.type == "link":
        content = {
            "url": post.link_url,
            "linkTitle": post.link_title,
            "linkDescription": post.link_description,
            "linkThumbnail": post.link_thumbnail
        }
    elif post.type == "file":
        # Get files from uploads relationship
        files = []
        if post.uploads:
            files = [
                {
                    "name": upload.original_name,
                    "url": upload.file_url,
                    "size": upload.file_size,
                    "type": upload.mime_type
                }
                for upload in post.uploads
            ]
        content = {"files": files}

    # Format Comment with replies
    Comment = []
    if post.Comment:
        # Group Comment by parent_id to build the tree structure
        comment_dict = {}
        root_Comment = []
        
        for comment in post.Comment:
            formatted_comment = format_comment_for_api(comment)
            comment_dict[comment.id] = formatted_comment
            
            if comment.parent_id is None:
                root_Comment.append(formatted_comment)
            else:
                # This will be handled in the second pass
                formatted_comment["parent_id"] = comment.parent_id
        
        # Second pass to build replies
        for comment in post.Comment:
            if comment.parent_id is not None:
                parent_comment = comment_dict.get(comment.parent_id)
                if parent_comment:
                    if "replies" not in parent_comment:
                        parent_comment["replies"] = []
                    parent_comment["replies"].append(comment_dict[comment.id])
        
        Comment = root_Comment

    # Format tags
    tags = []
    if post.tags:
        tags = [tag.name for tag in post.tags]

    return {
        "id": str(post.id),
        "title": post.title,
        "type": post.type,
        "author": user_data,
        "createdAt": post.created_at,
        "updatedAt": post.updated_at,
        "status": post.status,
        "tags": tags,
        "category": post.category or "",
        "likes": post.likes_count or 0,
        "shares": post.shares_count or 0,
        "saves": post.saves_count or 0,
        "viewCount": post.view_count or 0,
        "content": content,
        "Comment": Comment
    }


def format_comment_for_api(comment: Comment) -> Dict[str, Any]:
    """
    Format a comment database model into the TypeScript interface format
    """
    # Format user/author
    author_data = None
    if comment.user:
        author_data = {
            "id": str(comment.user.id),
            "email": comment.user.email,
            "username": comment.user.username,
            "full_name": comment.user.full_name,
            "website": comment.user.website,
            "image": comment.user.image,
            "joined_at": comment.user.joined_at
        }

    return {
        "id": str(comment.id),
        "author": author_data,
        "content": comment.body,
        "createdAt": comment.created_at,
        "likes": comment.likes_count or 0,
        "replies": []  # Will be populated by the parent function
    }


def update_post_counts(post: Post):
    """
    Update the cached counts for a post
    """
    # Update likes count
    post.likes_count = len(post.likes) if post.likes else 0
    
    # Update saves count
    post.saves_count = len(post.saves) if post.saves else 0
    
    # Update shares count
    post.shares_count = len(post.shares) if post.shares else 0
    
    # Update view count (this should be done separately when views are recorded)
    post.view_count = len(post.views) if post.views else 0


def update_comment_counts(comment: Comment):
    """
    Update the cached counts for a comment
    """
    comment.likes_count = len(comment.comment_likes) if comment.comment_likes else 0
