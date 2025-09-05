from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, BigInteger, Sequence, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Groups table
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, Sequence('groups_id_seq'), primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    users = relationship("User", back_populates="group")
    permissions = relationship("Permission", back_populates="group")

# Users table
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, Sequence('users_id_seq'), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, default=5)
    google_id = Column(String(255), unique=True)
    website = Column(String(500))
    image = Column(String(500))
    full_name = Column(String(255))
    approved = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("Group", back_populates="users")
    posts = relationship("Post", back_populates="user")
    categories = relationship("Category", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    tags = relationship("Tag", back_populates="user")
    uploads = relationship("Upload", back_populates="user")
    views = relationship("View", back_populates="user")
    likes = relationship("Like", back_populates="user")
    shares = relationship("Share", back_populates="user")

# Category table
class Category(Base):
    __tablename__ = "category"
    id = Column(Integer, Sequence('category_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_listed = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="categories")
    posts = relationship("Post", back_populates="category")

# Posts table
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, Sequence('posts_id_seq'), primary_key=True)
    type = Column(String(50), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"))
    body = Column(Text)
    caption = Column(Text)
    description = Column(Text)
    quote = Column(Text)
    quote_source = Column(String(255))
    link_url = Column(String(500))
    thumbnail = Column(String(500))
    user = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    attributes = relationship("PostAttribute", back_populates="post", uselist=False)
    uploads = relationship("Upload", back_populates="post")
    tags = relationship("Tag", back_populates="post")
    comments = relationship("Comment", back_populates="post")
    views = relationship("View", back_populates="post")
    likes = relationship("Like", back_populates="post")
    shares = relationship("Share", back_populates="post")
    pingbacks = relationship("Pingback", back_populates="post")

# Post attributes table
class PostAttribute(Base):
    __tablename__ = "post_attributes"
    id = Column(Integer, Sequence('post_attributes_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default='draft')
    pinned = Column(Boolean, nullable=False, default=False)
    slug = Column(String(500), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    original_work = Column(String(255))
    rights_holder = Column(String(255))
    license = Column(String(50), nullable=False, default='All Rights Reserved')
    scheduled_at = Column(DateTime(timezone=True))
    allow_comments = Column(Boolean, nullable=False, default=True)
    visibility = Column(String(20), nullable=False, default='public')
    visibility_groups = Column(String(500))  # JSON string for group IDs
    post = relationship("Post", back_populates="attributes")

# Uploads table
class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, Sequence('uploads_id_seq'), primary_key=True)
    url = Column(String(500), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"))
    type = Column(String(20), nullable=False)
    size = Column(BigInteger, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    name = Column(String(255), nullable=False)
    alternative_text = Column(String(500))
    source = Column(String(255))
    mime_type = Column(String(100))
    user = relationship("User", back_populates="uploads")
    post = relationship("Post", back_populates="uploads")

# Tags table
class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, Sequence('tags_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="published")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("Post", back_populates="tags")
    user = relationship("User", back_populates="tags")
    __table_args__ = (UniqueConstraint('post_id', 'name', name='_post_tag_uc'),)

# Comments table
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, Sequence('comments_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    parent_id = Column(Integer, ForeignKey("comments.id"))
    body = Column(Text, nullable=False)
    user_ip = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(String(20), nullable=False, default='pending')  # pending, approved, spam, denied
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id])

# Views table
class View(Base):
    __tablename__ = "views"
    id = Column(Integer, Sequence('views_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("Post", back_populates="views")
    user = relationship("User", back_populates="views")

# Likes table
class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, Sequence('likes_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")
    __table_args__ = (UniqueConstraint('post_id', 'user_id', name='_post_like_uc'),)

# Shares table
class Share(Base):
    __tablename__ = "shares"
    id = Column(Integer, Sequence('shares_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("Post", back_populates="shares")
    user = relationship("User", back_populates="shares")

# Pingbacks table
class Pingback(Base):
    __tablename__ = "pingbacks"
    id = Column(Integer, Sequence('pingbacks_id_seq'), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    source = Column(String(500), nullable=False)
    title = Column(Text, nullable=False)
    excerpt = Column(Text)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("Post", back_populates="pingbacks")

# Permissions table
class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, Sequence('permissions_id_seq'), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("Group", back_populates="permissions")
    __table_args__ = (UniqueConstraint('group_id', 'name', name='_group_permission_uc'),)

# Settings table
class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, Sequence('settings_id_seq'), primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    type = Column(String(20), default='string')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Modules table
class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=True)
    canDisable = Column(Boolean, nullable=True)
    canUninstall = Column(Boolean, nullable=True)
    conflicts = Column(Text, nullable=True)

# Feathers table
class Feather(Base):
    __tablename__ = "feathers"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=True)
    canDisable = Column(Boolean, nullable=True)

# Themes table
class Theme(Base):
    __tablename__ = "themes"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    isActive = Column(Boolean, nullable=True)
