import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class UserConfig:
    """Load and manage user configurations from .env"""
    
    @staticmethod
    def get_default_users() -> List[Dict]:
        """Load default users from environment variable"""
        try:
            users_json = os.getenv('DEFAULT_USERS', '[]')
            users = json.loads(users_json)
            
            # Validate user data
            required_fields = ['username', 'password', 'email', 'full_name', 'role']
            validated_users = []
            
            for user in users:
                if not all(field in user for field in required_fields):
                    print(f"⚠️ Warning: User {user.get('username', 'unknown')} is missing required fields")
                    continue
                
                # Validate role
                if user['role'] not in ['admin', 'hr']:
                    print(f"⚠️ Warning: User {user['username']} has invalid role: {user['role']}")
                    user['role'] = 'hr'  # Default to hr
                
                validated_users.append(user)
            
            return validated_users
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing DEFAULT_USERS from .env: {e}")
            return []
        except Exception as e:
            print(f"❌ Error loading user configuration: {e}")
            return []
    
    @staticmethod
    def get_session_config() -> Dict:
        """Get session configuration from environment"""
        return {
            'secret_key': os.getenv('SESSION_SECRET_KEY', 'default-secret-key-change-this'),
            'expiry_hours': int(os.getenv('SESSION_EXPIRY_HOURS', '24'))
        }
    
    @staticmethod
    def validate_env_config():
        """Validate that all required environment variables are set"""
        required_vars = ['DATABASE_URL', 'PERPLEXITY_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️ Warning: Missing environment variables: {', '.join(missing_vars)}")
            return False
        
        # Check if default users are configured
        users = UserConfig.get_default_users()
        if not users:
            print("⚠️ Warning: No default users configured in DEFAULT_USERS")
            return False
        
        print(f"✅ Environment configuration validated. {len(users)} users configured.")
        return True