-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS "permissions" CASCADE;
DROP TABLE IF EXISTS "pingbacks" CASCADE;
DROP TABLE IF EXISTS "shares" CASCADE;
DROP TABLE IF EXISTS "likes" CASCADE;
DROP TABLE IF EXISTS "views" CASCADE;
DROP TABLE IF EXISTS "comments" CASCADE;
DROP TABLE IF EXISTS "tags" CASCADE;
DROP TABLE IF EXISTS "post_attributes" CASCADE;
DROP TABLE IF EXISTS "uploads" CASCADE;
DROP TABLE IF EXISTS "posts" CASCADE;
DROP TABLE IF EXISTS "category" CASCADE;
DROP TABLE IF EXISTS "users" CASCADE;
DROP TABLE IF EXISTS "groups" CASCADE;
DROP TABLE IF EXISTS "settings" CASCADE;

-- Create sequences for auto-incrementing IDs
CREATE SEQUENCE IF NOT EXISTS groups_id_seq;
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE SEQUENCE IF NOT EXISTS category_id_seq;
CREATE SEQUENCE IF NOT EXISTS posts_id_seq;
CREATE SEQUENCE IF NOT EXISTS uploads_id_seq;
CREATE SEQUENCE IF NOT EXISTS post_attributes_id_seq;
CREATE SEQUENCE IF NOT EXISTS tags_id_seq;
CREATE SEQUENCE IF NOT EXISTS comments_id_seq;
CREATE SEQUENCE IF NOT EXISTS views_id_seq;
CREATE SEQUENCE IF NOT EXISTS likes_id_seq;
CREATE SEQUENCE IF NOT EXISTS shares_id_seq;
CREATE SEQUENCE IF NOT EXISTS pingbacks_id_seq;
CREATE SEQUENCE IF NOT EXISTS permissions_id_seq;
CREATE SEQUENCE IF NOT EXISTS settings_id_seq;

-- Groups table (create first as it's referenced by users)
CREATE TABLE "groups"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('groups_id_seq'),
    "name" VARCHAR(50) NOT NULL UNIQUE,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE "users"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('users_id_seq'),
    "username" VARCHAR(50) NOT NULL UNIQUE,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "hashed_password" VARCHAR(255),
    "group_id" INTEGER NOT NULL DEFAULT 5, -- Default to Guest
    "google_id" VARCHAR(255) UNIQUE,
    "website" VARCHAR(500),
    "image" VARCHAR(500),
    "full_name" VARCHAR(255),
    "approved" BOOLEAN NOT NULL DEFAULT TRUE,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "joined_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_group_id FOREIGN KEY ("group_id") REFERENCES "groups"("id") ON DELETE SET DEFAULT
);

-- Category table
CREATE TABLE "category"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('category_id_seq'),
    "user_id" INTEGER NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "slug" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_category_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE,
    UNIQUE("slug")
);

-- Posts table
CREATE TABLE "posts"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('posts_id_seq'),
    "type" VARCHAR(50) NOT NULL CHECK ("type" IN('text', 'image', 'video', 'audio', 'link', 'quote')),
    "url" VARCHAR(500) NOT NULL UNIQUE,
    "user_id" INTEGER NOT NULL,
    "title" VARCHAR(500) NOT NULL,
    "category_id" INTEGER,
    "body" TEXT,
    "caption" TEXT,
    "description" TEXT,
    "quote" TEXT,
    "quote_source" VARCHAR(255),
    "link_url" VARCHAR(500),
    "thumbnail" VARCHAR(500),
    CONSTRAINT fk_posts_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE,
    CONSTRAINT fk_posts_category_id FOREIGN KEY ("category_id") REFERENCES "category"("id") ON DELETE SET NULL
);

-- Post attributes table (renamed from post-attributes to follow naming conventions)
CREATE TABLE "post_attributes"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('post_attributes_id_seq'),
    "post_id" INTEGER NOT NULL UNIQUE,
    "status" VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (
        "status" IN('draft', 'public', 'private', 'scheduled', 'open', 'admin', 'member', 'friend', 'guest', 'banned')
    ),
    "pinned" BOOLEAN NOT NULL DEFAULT FALSE,
    "slug" VARCHAR(500) NOT NULL UNIQUE,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "original_work" VARCHAR(255),
    "rights_holder" VARCHAR(255),
    "license" VARCHAR(50) NOT NULL DEFAULT 'All Rights Reserved' CHECK (
        "license" IN('All Rights Reserved', 'Public Domain', 'Orphan Work', 'Crown Copyright')
    ),
    "scheduled_at" TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_post_attributes_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE
);

-- Uploads table
CREATE TABLE "uploads"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('uploads_id_seq'),
    "url" VARCHAR(500) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "post_id" INTEGER,
    "type" VARCHAR(20) NOT NULL CHECK ("type" IN('audio', 'video', 'image', 'file')),
    "size" BIGINT NOT NULL CHECK ("size" > 0),
    "uploaded_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "alternative_text" VARCHAR(500),
    "source" VARCHAR(255),
    "mime_type" VARCHAR(100),
    CONSTRAINT fk_uploads_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE,
    CONSTRAINT fk_uploads_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE
);

-- Tags table
CREATE TABLE "tags"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('tags_id_seq'),
    "post_id" INTEGER NOT NULL,
    "user_id" INTEGER NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tags_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE,
    CONSTRAINT fk_tags_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE,
    UNIQUE("post_id", "name")
);

-- Comments table
CREATE TABLE "comments"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('comments_id_seq'),
    "post_id" INTEGER NOT NULL,
    "user_id" INTEGER,
    "parent_id" INTEGER, -- For nested comments
    "body" TEXT NOT NULL,
    "user_ip" INET,
    "user_agent" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        "status" IN('pending', 'approved', 'denied', 'spam')
    ),
    CONSTRAINT fk_comments_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE,
    CONSTRAINT fk_comments_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL,
    CONSTRAINT fk_comments_parent_id FOREIGN KEY ("parent_id") REFERENCES "comments"("id") ON DELETE CASCADE
);

-- Views table
CREATE TABLE "views"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('views_id_seq'),
    "post_id" INTEGER NOT NULL,
    "user_id" INTEGER,
    "ip_address" INET,
    "user_agent" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_views_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE,
    CONSTRAINT fk_views_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL
);

-- Likes table
CREATE TABLE "likes"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('likes_id_seq'),
    "post_id" INTEGER NOT NULL,
    "user_id" INTEGER NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_likes_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE,
    CONSTRAINT fk_likes_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE,
    UNIQUE("post_id", "user_id")
);

-- Shares table
CREATE TABLE "shares"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('shares_id_seq'),
    "post_id" INTEGER NOT NULL,
    "user_id" INTEGER NOT NULL,
    "platform" VARCHAR(50), -- e.g., 'twitter', 'facebook', 'email'
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_shares_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE,
    CONSTRAINT fk_shares_user_id FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE
);

-- Pingbacks table
CREATE TABLE "pingbacks"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('pingbacks_id_seq'),
    "post_id" INTEGER NOT NULL,
    "source" VARCHAR(500) NOT NULL,
    "title" TEXT NOT NULL,
    "excerpt" TEXT,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK ("status" IN('pending', 'approved', 'denied', 'spam')),
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pingbacks_post_id FOREIGN KEY ("post_id") REFERENCES "posts"("id") ON DELETE CASCADE
);

-- Permissions table
CREATE TABLE "permissions"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('permissions_id_seq'),
    "group_id" INTEGER NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_permissions_group_id FOREIGN KEY ("group_id") REFERENCES "groups"("id") ON DELETE CASCADE,
    UNIQUE("group_id", "name")
);

-- Settings table
CREATE TABLE "settings"(
    "id" INTEGER PRIMARY KEY DEFAULT nextval('settings_id_seq'),
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "value" TEXT NOT NULL,
    "description" TEXT,
    "type" VARCHAR(20) DEFAULT 'string' CHECK ("type" IN('string', 'integer', 'boolean', 'json')),
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON "users"("email");
CREATE INDEX idx_users_username ON "users"("username");
CREATE INDEX idx_users_group_id ON "users"("group_id");
CREATE INDEX idx_posts_user_id ON "posts"("user_id");
CREATE INDEX idx_posts_category_id ON "posts"("category_id");
CREATE INDEX idx_posts_type ON "posts"("type");
CREATE INDEX idx_post_attributes_slug ON "post_attributes"("slug");
CREATE INDEX idx_post_attributes_status ON "post_attributes"("status");
CREATE INDEX idx_post_attributes_created_at ON "post_attributes"("created_at");
CREATE INDEX idx_comments_post_id ON "comments"("post_id");
CREATE INDEX idx_comments_user_id ON "comments"("user_id");
CREATE INDEX idx_comments_status ON "comments"("status");
CREATE INDEX idx_tags_post_id ON "tags"("post_id");
CREATE INDEX idx_tags_name ON "tags"("name");
CREATE INDEX idx_views_post_id ON "views"("post_id");
CREATE INDEX idx_likes_post_id ON "likes"("post_id");
CREATE INDEX idx_likes_user_id ON "likes"("user_id");

-- Insert predefined groups
INSERT INTO "groups" ("id", "name", "description") VALUES
(1, 'Admin', 'Full administrative access to all features'),
(2, 'Member', 'Regular registered users with standard permissions'),
(3, 'Friend', 'Trusted users with additional privileges'),
(4, 'Banned', 'Users who have been banned from the platform'),
(5, 'Guest', 'Anonymous or unregistered users with limited access');

-- Set the sequence values to continue from the inserted IDs
SELECT setval('groups_id_seq', 5, true);

-- Insert permissions for Admin group (ID: 1)
INSERT INTO "permissions" ("group_id", "name", "description") VALUES
(1, 'Add Comments', 'Can add comments to posts'),
(1, 'Add Comments to Private Posts', 'Can comment on private posts'),
(1, 'Add Drafts', 'Can create draft posts'),
(1, 'Add Groups', 'Can create user groups'),
(1, 'Add Pages', 'Can create pages'),
(1, 'Add Posts', 'Can create posts'),
(1, 'Add Uploads', 'Can upload files'),
(1, 'Add Users', 'Can create user accounts'),
(1, 'Change Settings', 'Can modify system settings'),
(1, 'Use HTML in Comments', 'Can use HTML markup in comments'),
(1, 'Delete Comments', 'Can delete any comments'),
(1, 'Delete Drafts', 'Can delete any drafts'),
(1, 'Delete Groups', 'Can delete user groups'),
(1, 'Delete Own Comments', 'Can delete own comments'),
(1, 'Delete Own Drafts', 'Can delete own drafts'),
(1, 'Delete Own Posts', 'Can delete own posts'),
(1, 'Delete Pages', 'Can delete pages'),
(1, 'Delete Webmentions', 'Can delete webmentions/pingbacks'),
(1, 'Delete Posts', 'Can delete any posts'),
(1, 'Delete Uploads', 'Can delete uploaded files'),
(1, 'Delete Users', 'Can delete user accounts'),
(1, 'Edit Comments', 'Can edit any comments'),
(1, 'Edit Drafts', 'Can edit any drafts'),
(1, 'Edit Groups', 'Can modify user groups'),
(1, 'Edit Own Comments', 'Can edit own comments'),
(1, 'Edit Own Drafts', 'Can edit own drafts'),
(1, 'Edit Own Posts', 'Can edit own posts'),
(1, 'Edit Pages', 'Can edit pages'),
(1, 'Edit Webmentions', 'Can edit webmentions/pingbacks'),
(1, 'Edit Posts', 'Can edit any posts'),
(1, 'Edit Uploads', 'Can edit uploaded file details'),
(1, 'Edit Users', 'Can edit user accounts'),
(1, 'Export Content', 'Can export site content'),
(1, 'Import Content', 'Can import content to the site'),
(1, 'Like Posts', 'Can like posts'),
(1, 'Manage Categories', 'Can create, edit, and delete categories'),
(1, 'Toggle Extensions', 'Can enable/disable extensions'),
(1, 'Unlike Posts', 'Can remove likes from posts'),
(1, 'View Drafts', 'Can view any draft posts'),
(1, 'View Own Drafts', 'Can view own draft posts'),
(1, 'View Pages', 'Can view pages'),
(1, 'View Private Posts', 'Can view private posts'),
(1, 'View Scheduled Posts', 'Can view scheduled posts'),
(1, 'View Site', 'Can access the website'),
(1, 'View Uploads', 'Can view uploaded files');

-- Insert basic permissions for Member group (ID: 2)
INSERT INTO "permissions" ("group_id", "name", "description") VALUES
(2, 'Add Comments', 'Can add comments to posts'),
(2, 'Add Drafts', 'Can create draft posts'),
(2, 'Add Posts', 'Can create posts'),
(2, 'Add Uploads', 'Can upload files'),
(2, 'Delete Own Comments', 'Can delete own comments'),
(2, 'Delete Own Drafts', 'Can delete own drafts'),
(2, 'Delete Own Posts', 'Can delete own posts'),
(2, 'Edit Own Comments', 'Can edit own comments'),
(2, 'Edit Own Drafts', 'Can edit own drafts'),
(2, 'Edit Own Posts', 'Can edit own posts'),
(2, 'Like Posts', 'Can like posts'),
(2, 'Unlike Posts', 'Can remove likes from posts'),
(2, 'View Own Drafts', 'Can view own draft posts'),
(2, 'View Site', 'Can access the website');

-- Insert permissions for Friend group (ID: 3)
INSERT INTO "permissions" ("group_id", "name", "description") VALUES
(3, 'Add Comments', 'Can add comments to posts'),
(3, 'Add Comments to Private Posts', 'Can comment on private posts'),
(3, 'Add Drafts', 'Can create draft posts'),
(3, 'Add Posts', 'Can create posts'),
(3, 'Add Uploads', 'Can upload files'),
(3, 'Delete Own Comments', 'Can delete own comments'),
(3, 'Delete Own Drafts', 'Can delete own drafts'),
(3, 'Delete Own Posts', 'Can delete own posts'),
(3, 'Edit Own Comments', 'Can edit own comments'),
(3, 'Edit Own Drafts', 'Can edit own drafts'),
(3, 'Edit Own Posts', 'Can edit own posts'),
(3, 'Like Posts', 'Can like posts'),
(3, 'Unlike Posts', 'Can remove likes from posts'),
(3, 'View Own Drafts', 'Can view own draft posts'),
(3, 'View Private Posts', 'Can view private posts'),
(3, 'View Site', 'Can access the website');

-- Insert minimal permissions for Guest group (ID: 5)
INSERT INTO "permissions" ("group_id", "name", "description") VALUES
(5, 'View Site', 'Can access the website');

-- Banned group (ID: 4) gets no permissions

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_post_attributes_updated_at BEFORE UPDATE ON "post_attributes" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON "comments" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON "settings" FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some basic settings
INSERT INTO "settings" ("name", "value", "description", "type") VALUES
('site_title', 'My CMS Portal', 'The title of the website', 'string'),
('site_description', 'A powerful content management system', 'The description of the website', 'string'),
('posts_per_page', '10', 'Number of posts to display per page', 'integer'),
('allow_comments', 'true', 'Whether comments are allowed on posts', 'boolean'),
('require_approval', 'true', 'Whether comments require approval before being shown', 'boolean');

COMMIT;