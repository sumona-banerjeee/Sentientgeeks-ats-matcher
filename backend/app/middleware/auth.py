from fastapi import HTTPException, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from ..models.user_models import User

def get_current_user_from_session(session_token: Optional[str], db: Session) -> Optional[User]:
    #Getting user from session token
    from ..api.user_routes import get_current_user_from_session as get_user
    return get_user(session_token, db)

def is_admin(user: User) -> bool:
    #Checking if user has admin role
    return user and user.role == "admin"

def is_hr(user: User) -> bool:
    #Checking if user has hr role
    return user and user.role == "hr"