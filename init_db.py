"""
Database initialization script
Creates default groups, permissions, settings, and admin user
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import async_session
from app.models import User, Group, Permission, Setting
from app.auth import get_password_hash


async def init_database():
    """Initialize database with default data"""
    async with async_session() as db:
        try:
            print("🚀 Initializing database...")
            
            # Step 1: Create Groups
            print("📁 Creating user groups...")
            groups_data = [
                (1, 'Admin', 'Full administrative access to all features'),
                (2, 'Member', 'Regular registered users with standard permissions'),
                (3, 'Friend', 'Trusted users with additional privileges'),
                (4, 'Banned', 'Users who have been banned from the platform'),
                (5, 'Guest', 'Anonymous or unregistered users with limited access')
            ]
            
            for group_id, name, description in groups_data:
                # Check if group already exists
                result = await db.execute(text("SELECT id FROM groups WHERE id = :id"), {"id": group_id})
                if not result.scalar():
                    await db.execute(
                        text("INSERT INTO groups (id, name, description) VALUES (:id, :name, :description)"),
                        {"id": group_id, "name": name, "description": description}
                    )
                    print(f"   ✅ Created group: {name}")
                else:
                    print(f"   ⚠️  Group already exists: {name}")
            
            # Set sequence value
            await db.execute(text("SELECT setval('groups_id_seq', 5, true)"))
            
            # Step 2: Create Admin Permissions
            print("🔑 Creating Admin permissions...")
            admin_permissions = [
                'Add Comments', 'Add Comments to Private Posts', 'Add Drafts', 'Add Groups',
                'Add Pages', 'Add Posts', 'Add Uploads', 'Add Users', 'Change Settings',
                'Use HTML in Comments', 'Delete Comments', 'Delete Drafts', 'Delete Groups',
                'Delete Own Comments', 'Delete Own Drafts', 'Delete Own Posts', 'Delete Pages',
                'Delete Webmentions', 'Delete Posts', 'Delete Uploads', 'Delete Users',
                'Edit Comments', 'Edit Drafts', 'Edit Groups', 'Edit Own Comments',
                'Edit Own Drafts', 'Edit Own Posts', 'Edit Pages', 'Edit Webmentions',
                'Edit Posts', 'Edit Uploads', 'Edit Users', 'Export Content', 'Import Content',
                'Like Posts', 'Manage Categories', 'Toggle Extensions', 'Unlike Posts',
                'View Drafts', 'View Own Drafts', 'View Pages', 'View Private Posts',
                'View Scheduled Posts', 'View Site', 'View Uploads'
            ]
            
            for perm_name in admin_permissions:
                result = await db.execute(
                    text("SELECT id FROM permissions WHERE group_id = 1 AND name = :name"),
                    {"name": perm_name}
                )
                if not result.scalar():
                    await db.execute(
                        text("INSERT INTO permissions (group_id, name, description) VALUES (1, :name, :desc)"),
                        {"name": perm_name, "desc": f"Admin permission: {perm_name}"}
                    )
            print(f"   ✅ Created {len(admin_permissions)} admin permissions")
            
            # Step 3: Create Member Permissions
            print("👤 Creating Member permissions...")
            member_permissions = [
                'Add Comments', 'Add Drafts', 'Add Posts', 'Add Uploads', 'Delete Own Comments',
                'Delete Own Drafts', 'Delete Own Posts', 'Edit Own Comments', 'Edit Own Drafts',
                'Edit Own Posts', 'Like Posts', 'Unlike Posts', 'View Own Drafts', 'View Site'
            ]
            
            for perm_name in member_permissions:
                result = await db.execute(
                    text("SELECT id FROM permissions WHERE group_id = 2 AND name = :name"),
                    {"name": perm_name}
                )
                if not result.scalar():
                    await db.execute(
                        text("INSERT INTO permissions (group_id, name, description) VALUES (2, :name, :desc)"),
                        {"name": perm_name, "desc": f"Member permission: {perm_name}"}
                    )
            print(f"   ✅ Created {len(member_permissions)} member permissions")
            
            # Step 4: Create Friend Permissions
            print("👥 Creating Friend permissions...")
            friend_permissions = [
                'Add Comments', 'Add Comments to Private Posts', 'Add Drafts', 'Add Posts',
                'Add Uploads', 'Delete Own Comments', 'Delete Own Drafts', 'Delete Own Posts',
                'Edit Own Comments', 'Edit Own Drafts', 'Edit Own Posts', 'Like Posts',
                'Unlike Posts', 'View Own Drafts', 'View Private Posts', 'View Site'
            ]
            
            for perm_name in friend_permissions:
                result = await db.execute(
                    text("SELECT id FROM permissions WHERE group_id = 3 AND name = :name"),
                    {"name": perm_name}
                )
                if not result.scalar():
                    await db.execute(
                        text("INSERT INTO permissions (group_id, name, description) VALUES (3, :name, :desc)"),
                        {"name": perm_name, "desc": f"Friend permission: {perm_name}"}
                    )
            print(f"   ✅ Created {len(friend_permissions)} friend permissions")
            
            # Step 5: Create Guest Permissions
            print("👻 Creating Guest permissions...")
            result = await db.execute(
                text("SELECT id FROM permissions WHERE group_id = 5 AND name = 'View Site'")
            )
            if not result.scalar():
                await db.execute(
                    text("INSERT INTO permissions (group_id, name, description) VALUES (5, 'View Site', 'Can access the website')")
                )
            print("   ✅ Created guest permissions")
            
            # Step 6: Create database functions and triggers
            print("⚙️  Creating database functions and triggers...")
            try:
                # Create function for updating timestamp
                await db.execute(text("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql'
                """))
                
                # Create triggers
                triggers = [
                    "CREATE TRIGGER update_post_attributes_updated_at BEFORE UPDATE ON post_attributes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
                    "CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
                    "CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
                ]
                
                for trigger in triggers:
                    try:
                        await db.execute(text(trigger))
                    except Exception:
                        # Trigger might already exist, ignore error
                        pass
                        
                print("   ✅ Database functions and triggers created")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not create triggers: {e}")
            
            # Step 7: Create Settings
            print("⚙️  Creating system settings...")
            settings_data = [
                ('site_title', 'My CMS Portal', 'The title of the website', 'string'),
                ('site_description', 'A powerful content management system', 'The description of the website', 'string'),
                ('posts_per_page', '10', 'Number of posts to display per page', 'integer'),
                ('allow_comments', 'true', 'Whether comments are allowed on posts', 'boolean'),
                ('require_approval', 'true', 'Whether comments require approval before being shown', 'boolean')
            ]
            
            for name, value, description, type_val in settings_data:
                result = await db.execute(
                    text("SELECT id FROM settings WHERE name = :name"),
                    {"name": name}
                )
                if not result.scalar():
                    await db.execute(
                        text("INSERT INTO settings (name, value, description, type) VALUES (:name, :value, :desc, :type)"),
                        {"name": name, "value": value, "desc": description, "type": type_val}
                    )
            print(f"   ✅ Created {len(settings_data)} system settings")
            
            # Step 8: Create Demo Admin User
            print("👑 Creating demo admin user...")
            result = await db.execute(
                text("SELECT id FROM users WHERE username = 'admin'")
            )
            if not result.scalar():
                await db.execute(text("""
                    INSERT INTO users (username, email, hashed_password, full_name, group_id, approved, is_active)
                    VALUES ('admin', 'admin@example.com', :password, 'System Administrator', 1, true, true)
                """), {"password": get_password_hash("admin123")})
                print("   ✅ Demo admin user created")
                print("      Username: admin")
                print("      Password: admin123")
                print("      ⚠️  IMPORTANT: Change this password immediately!")
            else:
                print("   ⚠️  Admin user already exists")
            
            await db.commit()
            print("✅ Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(init_database())
