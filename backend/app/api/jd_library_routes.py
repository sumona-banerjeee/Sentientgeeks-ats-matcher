from fastapi import APIRouter, HTTPException, Depends, Cookie
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..models.database import get_db
from ..models.jd_library_models import JDLibrary, JDUsageHistory
from ..api.user_routes import get_current_user_from_session

router = APIRouter(prefix="/api/jd-library", tags=["JD Library"])

@router.post("/save")
async def save_jd_to_library(
    jd_data: dict,
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """
    Save a processed JD to the library for reuse
    Required fields: jd_name, structured_data, skills_weightage
    """
    try:
        # Get current user
        current_user = get_current_user_from_session(session_token, db)
        
        # Validate required fields
        if not jd_data.get('jd_name'):
            raise HTTPException(status_code=400, detail="JD name is required")
        
        if not jd_data.get('structured_data'):
            raise HTTPException(status_code=400, detail="Structured data is required")
        
        structured = jd_data['structured_data']
        
        # Create library entry
        jd_library = JDLibrary(
            user_id=current_user.id if current_user else None,
            user_name=current_user.full_name if current_user else "Guest",
            jd_name=jd_data['jd_name'],
            job_title=structured.get('job_title', ''),
            company_name=structured.get('company', ''),
            location=structured.get('location', ''),
            job_type=structured.get('job_type', 'Full-time'),
            original_text=jd_data.get('original_text', ''),
            structured_data=structured,
            skills_weightage=jd_data.get('skills_weightage', {}),
            tags=jd_data.get('tags', []),
            notes=jd_data.get('notes', '')
        )
        
        db.add(jd_library)
        db.commit()
        db.refresh(jd_library)
        
        print(f"✅ JD saved to library: {jd_library.jd_name} (ID: {jd_library.id})")
        
        return {
            "status": "success",
            "message": "JD saved to library successfully",
            "jd_library_id": jd_library.id,
            "jd": jd_library.to_dict()
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        print(f"Error saving JD to library: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_jd_library(
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None),
    search: Optional[str] = None,
    tag: Optional[str] = None,
    active_only: bool = True
):
    """
    List all JDs in the library (with role-based filtering)
    - Admin: See all JDs
    - HR: See only their own JDs
    """
    try:
        current_user = get_current_user_from_session(session_token, db)
        
        query = db.query(JDLibrary)
        
        # Role-based filtering
        if current_user:
            if current_user.role == "hr":
                # HR sees only their own JDs
                query = query.filter(JDLibrary.user_id == current_user.id)
            # Admin sees all (no filter)
        else:
            # Guest sees only their own (no user_id)
            query = query.filter(JDLibrary.user_id == None)
        
        # Active filter
        if active_only:
            query = query.filter(JDLibrary.is_active == True)
        
        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (JDLibrary.jd_name.ilike(search_term)) |
                (JDLibrary.job_title.ilike(search_term)) |
                (JDLibrary.company_name.ilike(search_term))
            )
        
        # Tag filter
        if tag:
            # JSON array contains check
            query = query.filter(JDLibrary.tags.contains([tag]))
        
        # Get results, sorted by most recently used
        jd_list = query.order_by(
            JDLibrary.last_used_at.desc().nullslast(),
            JDLibrary.created_at.desc()
        ).all()
        
        return {
            "status": "success",
            "total": len(jd_list),
            "current_user": current_user.username if current_user else "Guest",
            "user_role": current_user.role if current_user else "guest",
            "jds": [jd.to_dict() for jd in jd_list]
        }
        
    except Exception as e:
        print(f"Error listing JD library: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/{jd_id}")
async def get_jd_from_library(
    jd_id: int,
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Get a specific JD from library by ID"""
    try:
        current_user = get_current_user_from_session(session_token, db)
        
        jd = db.query(JDLibrary).filter(JDLibrary.id == jd_id).first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found in library")
        
        # Permission check
        if current_user:
            if current_user.role == "hr" and jd.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            if jd.user_id is not None:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Update usage
        jd.usage_count += 1
        jd.last_used_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "jd": jd.to_dict()
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/{jd_id}")
async def update_jd_in_library(
    jd_id: int,
    update_data: dict,
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Update a JD in the library"""
    try:
        current_user = get_current_user_from_session(session_token, db)
        
        jd = db.query(JDLibrary).filter(JDLibrary.id == jd_id).first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found")
        
        # Permission check
        if current_user:
            if current_user.role == "hr" and jd.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            if jd.user_id is not None:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Update fields
        allowed_fields = ['jd_name', 'structured_data', 'skills_weightage', 'tags', 'notes', 'is_active']
        for field in allowed_fields:
            if field in update_data:
                setattr(jd, field, update_data[field])
        
        jd.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(jd)
        
        return {
            "status": "success",
            "message": "JD updated successfully",
            "jd": jd.to_dict()
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{jd_id}")
async def delete_jd_from_library(
    jd_id: int,
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Delete (or archive) a JD from library"""
    try:
        current_user = get_current_user_from_session(session_token, db)
        
        jd = db.query(JDLibrary).filter(JDLibrary.id == jd_id).first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found")
        
        # Permission check
        if current_user:
            if current_user.role == "hr" and jd.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            if jd.user_id is not None:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Soft delete (archive) instead of hard delete
        jd.is_active = False
        jd.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "message": "JD archived successfully"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/use/{jd_id}")
async def use_jd_from_library(
    jd_id: int,
    session_id: str,
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """
    Mark that a library JD is being used for a new matching session
    This tracks usage history
    """
    try:
        current_user = get_current_user_from_session(session_token, db)
        
        jd = db.query(JDLibrary).filter(JDLibrary.id == jd_id).first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found")
        
        # Create usage history record
        usage = JDUsageHistory(
            jd_library_id=jd_id,
            session_id=session_id,
            user_id=current_user.id if current_user else None
        )
        
        db.add(usage)
        
        # Update JD usage stats
        jd.usage_count += 1
        jd.last_used_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "success",
            "message": "JD usage tracked",
            "jd": jd.to_dict()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))