"""
Database Migration Manager
Supports both PostgreSQL and SQLite with automatic table creation
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

from backend.app.models.database import Base
from backend.app.models.user_models import User
from backend.app.models.jd_models import JobDescription, JDStructuringSession
from backend.app.models.resume_models import Resume, MatchingResult
from backend.app.models.history_models import MatchingHistory
from backend.app.models.jd_library_models import JDLibrary, JDUsageHistory
from backend.app.config.user_config import UserConfig


class DatabaseMigrationManager:
    """
    Universal Database Migration Manager
    Supports PostgreSQL, SQLite, MySQL
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize migration manager
        
        Args:
            database_url: Database connection string (optional, reads from .env if not provided)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment or parameters")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db_type = self._detect_database_type()
        
        print(f"✅ Migration Manager initialized for: {self.db_type}")
    
    def _detect_database_type(self) -> str:
        """Detect database type from URL"""
        url_lower = self.database_url.lower()
        
        if 'postgresql' in url_lower or 'postgres' in url_lower:
            return 'PostgreSQL'
        elif 'sqlite' in url_lower:
            return 'SQLite'
        elif 'mysql' in url_lower:
            return 'MySQL'
        else:
            return 'Unknown'
    
    def check_database_exists(self) -> bool:
        """Check if database is accessible"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables in database"""
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def create_all_tables(self, force: bool = False) -> Tuple[List[str], List[str]]:
        """
        Create all application tables
        
        Args:
            force: If True, drop existing tables first (DANGEROUS!)
        
        Returns:
            Tuple of (created_tables, existing_tables)
        """
        print("\n" + "="*70)
        print(f"🔧 DATABASE MIGRATION: {self.db_type}")
        print("="*70)
        
        existing_tables = self.get_existing_tables()
        print(f"\n📊 Existing tables: {len(existing_tables)}")
        
        if existing_tables:
            print("   " + "\n   ".join(existing_tables))
        
        if force:
            print("\n⚠️  WARNING: Dropping all existing tables...")
            Base.metadata.drop_all(bind=self.engine)
            print("   ✅ All tables dropped")
        
        print("\n🔨 Creating tables...")
        
        # Create all tables defined in models
        Base.metadata.create_all(bind=self.engine, checkfirst=True)
        
        # Get updated table list
        new_tables = self.get_existing_tables()
        created_tables = [t for t in new_tables if t not in existing_tables]
        
        print(f"\n✅ Migration completed!")
        print(f"   • Total tables: {len(new_tables)}")
        print(f"   • Newly created: {len(created_tables)}")
        
        if created_tables:
            print("\n📦 New tables created:")
            for table in created_tables:
                print(f"   ✓ {table}")
        
        return created_tables, existing_tables
    
    def verify_tables(self) -> Dict[str, bool]:
        """Verify all required tables exist"""
        required_tables = [
            'users',
            'job_descriptions',
            'jd_structuring_sessions',
            'resumes',
            'matching_results',
            'matching_history',
            'jd_library',
            'jd_usage_history'
        ]
        
        existing_tables = self.get_existing_tables()
        
        verification = {}
        for table in required_tables:
            verification[table] = table in existing_tables
        
        return verification
    
    def create_default_users(self) -> Tuple[int, int]:
        """
        Create default users from .env configuration
        
        Returns:
            Tuple of (created_count, skipped_count)
        """
        print("\n" + "="*70)
        print("👥 CREATING DEFAULT USERS")
        print("="*70)
        
        default_users = UserConfig.get_default_users()
        
        if not default_users:
            print("❌ No users configured in .env DEFAULT_USERS")
            return 0, 0
        
        db = self.SessionLocal()
        created_count = 0
        skipped_count = 0
        
        try:
            for user_data in default_users:
                # Check if user exists
                existing_user = db.query(User).filter(
                    User.username == user_data['username']
                ).first()
                
                if existing_user:
                    print(f"⚠️  User '{user_data['username']}' already exists - skipping")
                    skipped_count += 1
                    continue
                
                # Create new user
                new_user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    role=user_data.get('role', 'hr')
                )
                new_user.set_password(user_data['password'])
                
                db.add(new_user)
                created_count += 1
                print(f"✅ Created user: {user_data['username']} ({user_data['role']})")
            
            db.commit()
            
            print(f"\n📊 Summary:")
            print(f"   • Users created: {created_count}")
            print(f"   • Users skipped: {skipped_count}")
            print(f"   • Total users: {len(default_users)}")
            
            return created_count, skipped_count
        
        except Exception as e:
            db.rollback()
            print(f"❌ Error creating users: {e}")
            raise
        finally:
            db.close()
    
    def run_full_migration(self, create_users: bool = True, force: bool = False):
        """
        Run complete database migration
        
        Args:
            create_users: Whether to create default users
            force: Force recreate tables (DANGEROUS!)
        """
        print("\n" + "="*70)
        print("🚀 FULL DATABASE MIGRATION")
        print("="*70)
        
        # Step 1: Check database connection
        if not self.check_database_exists():
            print("❌ Cannot connect to database. Aborting migration.")
            return False
        
        # Step 2: Create tables
        created, existing = self.create_all_tables(force=force)
        
        # Step 3: Verify tables
        verification = self.verify_tables()
        print("\n🔍 Table Verification:")
        for table, exists in verification.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {table}")
        
        all_tables_exist = all(verification.values())
        
        if not all_tables_exist:
            print("\n❌ Some required tables are missing!")
            return False
        
        # Step 4: Create default users (if requested)
        if create_users:
            created_users, skipped_users = self.create_default_users()
        
        print("\n" + "="*70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"\nDatabase: {self.db_type}")
        print(f"Tables: {len(self.get_existing_tables())}")
        
        if create_users:
            print(f"Users: {created_users} created, {skipped_users} existing")
        
        print("\n🎉 Your database is ready!")
        
        return True
    
    def get_migration_status(self) -> Dict:
        """Get comprehensive migration status"""
        return {
            'database_type': self.db_type,
            'database_url': self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url,
            'connection': self.check_database_exists(),
            'tables': self.get_existing_tables(),
            'table_count': len(self.get_existing_tables()),
            'verification': self.verify_tables()
        }


def migrate_database(database_url: str = None, create_users: bool = True, force: bool = False):
    """
    Convenience function to run migration
    
    Args:
        database_url: Database URL (optional, reads from .env)
        create_users: Create default users from .env
        force: Force recreate tables
    """
    manager = DatabaseMigrationManager(database_url)
    return manager.run_full_migration(create_users=create_users, force=force)


if __name__ == "__main__":
    # Run migration when executed directly
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Migration Manager')
    parser.add_argument('--force', action='store_true', help='Force recreate all tables (DANGEROUS!)')
    parser.add_argument('--no-users', action='store_true', help='Skip creating default users')
    parser.add_argument('--db-url', type=str, help='Override database URL')
    
    args = parser.parse_args()
    
    migrate_database(
        database_url=args.db_url,
        create_users=not args.no_users,
        force=args.force
    )