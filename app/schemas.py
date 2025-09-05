
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    website: Optional[str] = None
    group_id: Optional[int] = 5
    google_id: Optional[str] = None
    image: Optional[str] = None
    approved: Optional[bool] = True
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    website: Optional[str] = None
    group_id: Optional[int] = None
    google_id: Optional[str] = None
    image: Optional[str] = None
    approved: Optional[bool] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    joined_at: Optional[datetime] = None

# Group schemas
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class GroupResponse(GroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Category schemas
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    user_id: int
    is_listed: Optional[bool] = True
    display_order: Optional[int] = 0

class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    is_listed: Optional[bool] = True
    display_order: Optional[int] = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_listed: Optional[bool] = None
    display_order: Optional[int] = None

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Post schemas
class PostBase(BaseModel):
    type: str
    url: str
    user_id: int
    title: str
    category_id: Optional[int] = None
    body: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    quote: Optional[str] = None
    quote_source: Optional[str] = None
    link_url: Optional[str] = None
    thumbnail: Optional[str] = None

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    type: Optional[str] = None
    url: Optional[str] = None
    user_id: Optional[int] = None
    title: Optional[str] = None
    category_id: Optional[int] = None
    body: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    quote: Optional[str] = None
    quote_source: Optional[str] = None
    link_url: Optional[str] = None
    thumbnail: Optional[str] = None

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user: Optional[UserResponse] = None
    category: Optional[CategoryResponse] = None
    created_at: Optional[datetime] = None

# PostAttribute schemas
class PostAttributeBase(BaseModel):
    post_id: int
    status: str
    pinned: bool
    slug: str
    original_work: Optional[str] = None
    rights_holder: Optional[str] = None
    license: Optional[str] = None
    scheduled_at: Optional[datetime] = None

class PostAttributeCreate(PostAttributeBase):
    pass

class PostAttributeUpdate(BaseModel):
    status: Optional[str] = None
    pinned: Optional[bool] = None
    slug: Optional[str] = None
    original_work: Optional[str] = None
    rights_holder: Optional[str] = None
    license: Optional[str] = None
    scheduled_at: Optional[datetime] = None

class PostAttributeResponse(PostAttributeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Upload schemas
class UploadBase(BaseModel):
    url: str
    user_id: int
    post_id: Optional[int] = None
    type: str
    size: int
    name: str
    alternative_text: Optional[str] = None
    source: Optional[str] = None
    mime_type: Optional[str] = None

class UploadCreate(UploadBase):
    pass

class UploadUpdate(BaseModel):
    url: Optional[str] = None
    user_id: Optional[int] = None
    post_id: Optional[int] = None
    type: Optional[str] = None
    size: Optional[int] = None
    name: Optional[str] = None
    alternative_text: Optional[str] = None
    source: Optional[str] = None
    mime_type: Optional[str] = None

class UploadResponse(UploadBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uploaded_at: Optional[datetime] = None

# Tag schemas
class TagBase(BaseModel):
    post_id: int
    user_id: int
    name: str

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    post_id: Optional[int] = None
    user_id: Optional[int] = None
    name: Optional[str] = None

class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Comment schemas
class CommentBase(BaseModel):
    post_id: int
    user_id: Optional[int] = None
    parent_id: Optional[int] = None
    body: str
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    status: Optional[str] = "pending"

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    post_id: Optional[int] = None
    user_id: Optional[int] = None
    parent_id: Optional[int] = None
    body: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    status: Optional[str] = None

class CommentResponse(CommentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# View schemas
class ViewBase(BaseModel):
    post_id: int
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class ViewCreate(ViewBase):
    pass

class ViewUpdate(BaseModel):
    post_id: Optional[int] = None
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class ViewResponse(ViewBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Like schemas
class LikeBase(BaseModel):
    post_id: int
    user_id: int

class LikeCreate(LikeBase):
    pass

class LikeUpdate(BaseModel):
    post_id: Optional[int] = None
    user_id: Optional[int] = None

class LikeResponse(LikeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Share schemas
class ShareBase(BaseModel):
    post_id: int
    user_id: int
    platform: Optional[str] = None

class ShareCreate(ShareBase):
    pass

class ShareUpdate(BaseModel):
    post_id: Optional[int] = None
    user_id: Optional[int] = None
    platform: Optional[str] = None

class ShareResponse(ShareBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Pingback schemas
class PingbackBase(BaseModel):
    post_id: int
    source: str
    title: str
    excerpt: Optional[str] = None
    status: Optional[str] = "pending"

class PingbackCreate(PingbackBase):
    pass

class PingbackUpdate(BaseModel):
    post_id: Optional[int] = None
    source: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    status: Optional[str] = None

class PingbackResponse(PingbackBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Permission schemas
class PermissionBase(BaseModel):
    group_id: int
    name: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    group_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None

class PermissionResponse(PermissionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None

# Setting schemas
class SettingBase(BaseModel):
    name: str
    value: str
    description: Optional[str] = None
    type: Optional[str] = "string"

class SettingCreate(SettingBase):
    pass

class SettingUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None

class SettingResponse(SettingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Admin Settings schemas
class UpdateSettingData(BaseModel):
    value: str
    type: Optional[Literal["string", "boolean", "number", "json"]] = "string"
    description: Optional[str] = None

class UpdateSettingsData(BaseModel):
    settings: Dict[str, UpdateSettingData]

class AdminSettingsResponse(BaseModel):
    success: bool
    data: List[SettingResponse]
    message: Optional[str] = None

class UpdateSettingsResponse(BaseModel):
    success: bool
    data: List[SettingResponse]
    message: Optional[str] = None

class SingleSettingResponse(BaseModel):
    success: bool
    data: SettingResponse
    message: Optional[str] = None


# File upload schema
class FileUpload(BaseModel):
    name: str
    url: str
    size: int
    type: str


# Post content schemas
class PostContent(BaseModel):
    # Text post
    body: Optional[str] = None

    # Photo post
    images: Optional[List[str]] = None
    caption: Optional[str] = None

    # Video post
    video_url: Optional[str] = None
    video_thumbnail: Optional[str] = None

    # Audio post
    audio_url: Optional[str] = None
    duration: Optional[str] = None
    audio_description: Optional[str] = None

    # Quote post
    quote: Optional[str] = None
    source: Optional[str] = None

    # Link post
    url: Optional[str] = None
    link_title: Optional[str] = None
    link_description: Optional[str] = None
    link_thumbnail: Optional[str] = None

    # File post
    files: Optional[List[FileUpload]] = None


PostType = Literal["text", "photo", "video", "audio", "quote", "link", "file"]
PostStatus = Literal["published", "draft", "private", "scheduled"]


class PostBase(BaseModel):
    title: Optional[str] = ""
    type: Optional[PostType] = "text"
    feather: Optional[str] = ""  # Keep for backward compatibility
    clean: Optional[str] = ""
    url: Optional[str] = ""
    pinned: Optional[bool] = False
    status: Optional[PostStatus] = "published"
    user_id: Optional[int] = 0
    category: Optional[str] = ""
    tag_names: Optional[List[str]] = []  # For creating posts with tag names
    
    # Content fields
    body: Optional[str] = None
    images: Optional[List[str]] = None
    caption: Optional[str] = None
    video_url: Optional[str] = None
    video_thumbnail: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[str] = None
    audio_description: Optional[str] = None
    quote: Optional[str] = None
    quote_source: Optional[str] = None
    link_url: Optional[str] = None
    link_title: Optional[str] = None
    link_description: Optional[str] = None
    link_thumbnail: Optional[str] = None


class PostCreate(PostBase):
    title: str


class PostUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[PostType] = None
    feather: Optional[str] = None
    clean: Optional[str] = None
    url: Optional[str] = None
    pinned: Optional[bool] = None
    status: Optional[PostStatus] = None
    category: Optional[str] = None
    tag_names: Optional[List[str]] = None
    
    # Content fields
    body: Optional[str] = None
    images: Optional[List[str]] = None
    caption: Optional[str] = None
    video_url: Optional[str] = None
    video_thumbnail: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[str] = None
    audio_description: Optional[str] = None
    quote: Optional[str] = None
    quote_source: Optional[str] = None
    link_url: Optional[str] = None
    link_title: Optional[str] = None
    link_description: Optional[str] = None
    link_thumbnail: Optional[str] = None


# Forward declare CommentResponse for circular reference
class CommentResponse(BaseModel):
    pass


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    likes_count: Optional[int] = 0
    shares_count: Optional[int] = 0
    saves_count: Optional[int] = 0
    view_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = None
    tags: Optional[List[TagResponse]] = []  # Actual tag objects
    content: Optional[PostContent] = None
    comments: Optional[List[CommentResponse]] = []


class PageBase(BaseModel):
    title: Optional[str] = ""
    body: Optional[str] = None
    public: Optional[bool] = True
    show_in_list: Optional[bool] = True
    list_order: Optional[int] = 0
    clean: Optional[str] = ""
    url: Optional[str] = ""
    user_id: Optional[int] = 0
    parent_id: Optional[int] = 0


class PageCreate(PageBase):
    title: str


class PageUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    public: Optional[bool] = None
    show_in_list: Optional[bool] = None
    list_order: Optional[int] = None
    clean: Optional[str] = None
    url: Optional[str] = None
    parent_id: Optional[int] = None


class PageResponse(PageBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = None


class CommentBase(BaseModel):
    body: Optional[str] = None
    author: Optional[str] = ""
    author_url: Optional[str] = ""
    author_email: Optional[str] = ""
    author_ip: Optional[int] = 0
    author_agent: Optional[str] = ""
    status: Optional[str] = "denied"
    post_id: Optional[int] = 0
    user_id: Optional[int] = 0
    parent_id: Optional[int] = None
    notify: Optional[bool] = False


class CommentCreate(CommentBase):
    body: str
    post_id: int


class CommentUpdate(BaseModel):
    body: Optional[str] = None
    status: Optional[str] = None
    notify: Optional[bool] = None


# Update the CommentResponse class to include likes and replies
CommentResponse.model_rebuild()


class CommentResponse(CommentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    likes_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = None
    author: Optional[UserResponse] = None  # Same as user but following the interface
    replies: Optional[List['CommentResponse']] = []


class CategorizeBase(BaseModel):
    name: str
    clean: str
    show_on_home: Optional[bool] = True


class CategorizeCreate(CategorizeBase):
    pass


class CategorizeUpdate(BaseModel):
    name: Optional[str] = None
    clean: Optional[str] = None
    show_on_home: Optional[bool] = None


class CategorizeResponse(CategorizeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class GroupBase(BaseModel):
    name: Optional[str] = ""


class GroupCreate(GroupBase):
    name: str


class GroupUpdate(BaseModel):
    name: Optional[str] = None


class GroupResponse(GroupBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class LikeBase(BaseModel):
    post_id: int
    user_id: int
    session_hash: str


class LikeCreate(LikeBase):
    pass


class LikeResponse(LikeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    timestamp: Optional[datetime] = None


class ViewBase(BaseModel):
    post_id: int
    user_id: Optional[int] = 0


class ViewCreate(ViewBase):
    pass


class ViewResponse(ViewBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: Optional[datetime] = None


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Upload schemas
class UploadBase(BaseModel):
    filename: str
    original_name: str
    file_path: str
    file_url: str
    file_size: int
    mime_type: str
    file_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    alt_text: Optional[str] = ""
    user_id: int
    post_id: Optional[int] = None
    is_public: Optional[bool] = True


class UploadCreate(UploadBase):
    pass


class UploadUpdate(BaseModel):
    alt_text: Optional[str] = None
    is_public: Optional[bool] = None
    post_id: Optional[int] = None


class UploadResponse(UploadBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: Optional[datetime] = None
    user: Optional[UserResponse] = None


# Post interaction schemas
class PostSaveBase(BaseModel):
    post_id: int
    user_id: int


class PostSaveCreate(PostSaveBase):
    pass


class PostSaveResponse(PostSaveBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: Optional[datetime] = None


class PostShareBase(BaseModel):
    post_id: int
    user_id: int
    platform: Optional[str] = ""


class PostShareCreate(PostShareBase):
    pass


class PostShareResponse(PostShareBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    shared_at: Optional[datetime] = None


class CommentLikeBase(BaseModel):
    comment_id: int
    user_id: int
    session_hash: str


class CommentLikeCreate(CommentLikeBase):
    pass


class CommentLikeResponse(CommentLikeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    timestamp: Optional[datetime] = None


# Update the forward references
PostResponse.model_rebuild()
CommentResponse.model_rebuild()


# NextAuth.js specific schemas
class UserSignUp(BaseModel):
    email: str
    username: str
    password: str
    name: Optional[str] = None


class UserSignIn(BaseModel):
    email: str
    password: str


class GoogleUser(BaseModel):
    email: str
    name: Optional[str] = None
    google_id: str
    image: Optional[str] = None


class GoogleUserCreate(BaseModel):
    email: str
    name: Optional[str] = None
    username: str
    google_id: str
    image: Optional[str] = None


class UserAuthResponse(BaseModel):
    """Response model for authentication endpoints with role and token"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    website: Optional[str] = None
    image: Optional[str] = None
    group_id: int
    role: str  # Based on group_id mapping
    is_active: bool
    approved: bool
    joined_at: Optional[datetime] = None
    access_token: str
    token_type: str = "bearer"
    
    model_config = ConfigDict(from_attributes=True)


# Admin Category schemas
class CreateCategoryData(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    is_listed: Optional[bool] = Field(True, alias="isListed")
    display_order: Optional[int] = Field(0, alias="displayOrder")

class UpdateCategoryData(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_listed: Optional[bool] = Field(None, alias="isListed")
    display_order: Optional[int] = Field(None, alias="displayOrder")

class AdminCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_listed: bool = Field(alias="isListed")
    display_order: int = Field(alias="displayOrder")
    post_count: int = Field(alias="postCount")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

class CategoryStatsResponse(BaseModel):
    total: int
    listed: int
    unlisted: int
    total_posts: int

class CategoryPaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    total_categories: int
    limit: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None

class CategoryFilters(BaseModel):
    search: Optional[str] = None
    is_listed: Optional[bool] = None

class AdminCategoriesResponse(BaseModel):
    data: List[AdminCategoryResponse]
    pagination: CategoryPaginationInfo
    filters: CategoryFilters

class BulkDeleteRequest(BaseModel):
    ids: List[int]

class ReorderCategoriesRequest(BaseModel):
    category_ids: List[int]


# Comment schemas
class CommentBase(BaseModel):
    id: int
    body: str
    author: str  # Will be populated from user.username or user.full_name
    email: str   # Will be populated from user.email
    url: Optional[str] = None  # Will be populated from user.website
    ip: str      # user_ip field
    status: Literal['pending', 'approved', 'spam', 'denied']
    created_at: datetime
    updated_at: datetime

class CommentResponse(CommentBase):
    model_config = ConfigDict(from_attributes=True)

class PostInfo(BaseModel):
    id: int
    title: str
    url: str
    model_config = ConfigDict(from_attributes=True)

class PostWithComments(BaseModel):
    post: PostInfo
    comments: List[CommentResponse]

class CommentUpdateStatus(BaseModel):
    status: Literal['pending', 'approved', 'spam', 'denied']

class CommentBatchRequest(BaseModel):
    comment_ids: List[int] = Field(alias="commentIds")
    action: Literal['approve', 'deny', 'spam', 'delete']

class CommentPaginationInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    page: int
    limit: int
    total: int
    pages: int
    has_next: bool = Field(alias="hasNext")
    has_prev: bool = Field(alias="hasPrev")

class CommentStats(BaseModel):
    total: int
    pending: int
    approved: int
    spam: int
    denied: int

class CommentsResponse(BaseModel):
    data: List[PostWithComments]  # Changed to grouped format
    pagination: CommentPaginationInfo
    stats: CommentStats

class CommentBatchResponse(BaseModel):
    success: bool
    processed: int
    errors: Optional[List[Dict[str, str]]] = None

# Spam schemas (using same Comment structure but filtered by status='spam')
class SpamItemResponse(CommentBase):
    """Spam items are just comments with status='spam'"""
    model_config = ConfigDict(from_attributes=True)

class PostWithSpamItems(BaseModel):
    post: PostInfo
    comments: List[SpamItemResponse]  # Using same structure but called comments for consistency
    model_config = ConfigDict(from_attributes=True)

class SpamBatchRequest(BaseModel):
    spam_ids: List[int] = Field(alias="spamIds")
    action: Literal['approve', 'reject', 'delete']

class SpamStats(BaseModel):
    total: int
    spam: int
    approved: int
    rejected: int  # This will be 'denied' status in database

class SpamResponse(BaseModel):
    data: List[PostWithSpamItems]  # Changed to grouped format
    pagination: CommentPaginationInfo
    stats: SpamStats

class SpamBatchResponse(BaseModel):
    success: bool
    processed: int
    errors: Optional[List[Dict[str, str]]] = None

class MarkCommentAsSpamRequest(BaseModel):
    comment_id: int = Field(alias="commentId")


# Post with Comments schemas for grouped view
class PostInfo(BaseModel):
    id: int
    title: str
    url: str
    model_config = ConfigDict(from_attributes=True)

class CommentInPost(BaseModel):
    id: int
    body: str
    author: str
    email: str
    url: Optional[str] = None
    ip: str
    status: Literal['pending', 'approved', 'spam', 'denied']
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

class PostWithComments(BaseModel):
    post: PostInfo
    comments: List[CommentInPost]
    comment_count: int = Field(alias="commentCount")

class GroupedCommentsResponse(BaseModel):
    data: List[PostWithComments]
    pagination: CommentPaginationInfo
    stats: CommentStats

# Module schemas
class ModuleBase(BaseModel):
    name: str
    description: str
    status: Optional[str] = None
    canDisable: Optional[bool] = None
    canUninstall: Optional[bool] = None
    conflicts: Optional[str] = None

class ModuleResponse(ModuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class ModuleUpdate(BaseModel):
    status: Optional[str] = None

class ModulesResponse(BaseModel):
    data: List[ModuleResponse]
    total: int

# Feather schemas
class FeatherBase(BaseModel):
    name: str
    description: str
    status: Optional[str] = None
    canDisable: Optional[bool] = None

class FeatherResponse(FeatherBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class FeatherUpdate(BaseModel):
    status: Optional[str] = None

class FeathersResponse(BaseModel):
    data: List[FeatherResponse]
    total: int

# Theme schemas
class ThemeBase(BaseModel):
    name: str
    description: str
    isActive: Optional[bool] = None

class ThemeResponse(ThemeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class ThemeUpdate(BaseModel):
    isActive: Optional[bool] = None

class ThemesResponse(BaseModel):
    data: List[ThemeResponse]
    total: int
