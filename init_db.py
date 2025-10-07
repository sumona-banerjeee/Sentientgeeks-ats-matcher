from backend.app.models.database import Base, engine, SessionLocal
from backend.app.models.user_models import User
from backend.app.config.user_config import UserConfig

def init_database():
    """Initialize database with tables and users from .env"""
    print("🔧 Initializing database...")
    
    # Validate environment
    UserConfig.validate_env_config()
    
    # Create all tables (including users table)
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")
    
    # Load users from .env
    default_users = UserConfig.get_default_users()
    
    if not default_users:
        print("⚠️ No users found in .env file")
        print("💡 Add DEFAULT_USERS to your .env file")
        return
    
    db = SessionLocal()
    try:
        users_created = 0
        users_skipped = 0
        
        for user_data in default_users:
            existing_user = db.query(User).filter(
                User.username == user_data['username']
            ).first()
            
            if existing_user:
                print(f"ℹ️  User '{user_data['username']}' already exists - skipping")
                users_skipped += 1
                continue
            
            new_user = User(
                username=user_data['username'],
                email=user_data['email'],
                full_name=user_data['full_name'],
                role=user_data.get('role', 'hr')
            )
            new_user.set_password(user_data['password'])
            
            db.add(new_user)
            users_created += 1
            print(f"✅ Created user: {user_data['username']} ({user_data['role']})")
        
        db.commit()
        
        print(f"\n📊 Summary:")
        print(f"   • Users created: {users_created}")
        print(f"   • Users skipped: {users_skipped}")
        print(f"   • Total users: {len(default_users)}")
        
        if users_created > 0:
            print(f"\n🔐 Credentials stored in .env file")
            print(f"⚠️  Change passwords in production!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
