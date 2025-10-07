from fastapi import APIRouter, HTTPException, Depends, Response, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from ..models.database import get_db
from ..models.user_models import User
from ..config.user_config import UserConfig
import secrets

router = APIRouter(prefix="/api/users", tags=["Users"])

class UserLogin(BaseModel):
    username: str
    password: str

# In-memory session storage
active_sessions = {}

def get_session_config():
    return UserConfig.get_session_config()

@router.post("/login")
async def login_user(login_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login user and create session"""
    try:
        user = db.query(User).filter(User.username == login_data.username).first()
        
        if not user or not user.check_password(login_data.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is inactive")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        session_config = get_session_config()
        session_token = secrets.token_urlsafe(32)
        
        expiry_time = datetime.utcnow() + timedelta(hours=session_config['expiry_hours'])
        active_sessions[session_token] = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'expires_at': expiry_time
        }
        
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=session_config['expiry_hours'] * 3600,
            samesite='lax'
        )
        
        print(f"✅ User '{user.username}' ({user.role}) logged in successfully")
        
        return {
            "status": "success",
            "message": "Login successful",
            "user": user.to_dict(),
            "session_token": session_token
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/logout")
async def logout_user(session_token: Optional[str] = Cookie(None), response: Response = None):
    """Logout user"""
    try:
        if session_token and session_token in active_sessions:
            username = active_sessions[session_token].get('username', 'unknown')
            del active_sessions[session_token]
            print(f"✅ User '{username}' logged out")
        
        if response:
            response.delete_cookie("session_token")
        
        return {"status": "success", "message": "Logged out successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

@router.get("/current")
async def get_current_user(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    """Get current logged-in user"""
    try:
        if not session_token or session_token not in active_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session_data = active_sessions[session_token]
        
        if datetime.utcnow() > session_data['expires_at']:
            del active_sessions[session_token]
            raise HTTPException(status_code=401, detail="Session expired")
        
        user = db.query(User).filter(User.id == session_data['user_id']).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "user": user.to_dict()
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/validate")
async def validate_session(session_token: Optional[str] = Cookie(None)):
    """Validate session"""
    if not session_token or session_token not in active_sessions:
        return {"status": "invalid", "authenticated": False}
    
    session_data = active_sessions[session_token]
    
    if datetime.utcnow() > session_data['expires_at']:
        del active_sessions[session_token]
        return {"status": "expired", "authenticated": False}
    
    return {
        "status": "valid",
        "authenticated": True,
        "username": session_data['username'],
        "role": session_data['role']
    }

def get_current_user_from_session(session_token: Optional[str], db: Session) -> Optional[User]:
    """Helper function to get current user"""
    if not session_token or session_token not in active_sessions:
        return None
    
    session_data = active_sessions[session_token]
    
    if datetime.utcnow() > session_data['expires_at']:
        del active_sessions[session_token]
        return None
    
    return db.query(User).filter(User.id == session_data['user_id']).first()