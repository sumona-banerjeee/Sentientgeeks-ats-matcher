from fastapi import APIRouter, HTTPException, Depends, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from ..models.database import get_db
from ..models.resume_models import MatchingResult, Resume
from ..models.jd_models import JobDescription
from ..models.history_models import MatchingHistory
from datetime import datetime

router = APIRouter(prefix="/api/history", tags=["History"])

@router.post("/save/{session_id}")
async def save_matching_history(
    session_id: str, 
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Save matching session with automatic user tracking"""
    try:
        # Getting current user like who is doing the matching
        from ..api.user_routes import get_current_user_from_session
        current_user = get_current_user_from_session(session_token, db)
        
        jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
        results = db.query(MatchingResult).filter(
            MatchingResult.session_id == session_id
        ).order_by(MatchingResult.overall_score.desc()).all()
        
        if not jd or not results:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        jd_data = jd.structured_data or {}
        job_title = jd_data.get('job_title', 'Unknown Position')
        company_name = jd_data.get('company', 'Unknown Company')
        
        top_result = results[0]
        top_resume = db.query(Resume).filter(Resume.id == top_result.resume_id).first()
        top_candidate_name = "Unknown Candidate"
        if top_resume and top_resume.structured_data:
            top_candidate_name = top_resume.structured_data.get('name', top_resume.filename.replace('.pdf', ''))
        
        # It is a AUTOMATIC USER TRACKING
        history_record = MatchingHistory(
            session_id=session_id,
            user_id=current_user.id if current_user else None,
            user_name=current_user.full_name if current_user else "Guest",  # Store full name
            job_title=job_title,
            company_name=company_name,
            total_resumes=len(results),
            successful_matches=len([r for r in results if r.overall_score >= 40]),
            top_candidate_name=top_candidate_name,
            top_candidate_score=top_result.overall_score,
            matching_summary={
                'total_candidates': len(results),
                'average_score': sum(r.overall_score for r in results) / len(results),
                'top_candidates': [{'rank': i+1, 'score': r.overall_score} for i, r in enumerate(results[:5])]
            }
        )
        
        db.add(history_record)
        db.commit()
        
        user_info = f"{current_user.full_name} ({current_user.role})" if current_user else "Guest"
        print(f"History saved for session {session_id} by {user_info}")
        
        return {
            "status": "success", 
            "message": "History saved successfully",
            "created_by": current_user.full_name if current_user else "Guest"
        }
    
    except Exception as e:
        db.rollback()
        print(f"Error saving history: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/list")
async def get_matching_history(
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """
    Get history with role-based filtering:
    - Admin: See ALL history from ALL HR users
    - HR: See ONLY their own history
    """
    try:
        from ..api.user_routes import get_current_user_from_session
        current_user = get_current_user_from_session(session_token, db)
        
        query = db.query(MatchingHistory)
        
        if current_user:
            if current_user.role == "admin":
                # Admin will be able to see every history created by the all the hr and created by him.
                print(f"Admin '{current_user.username}' accessing ALL history")
            elif current_user.role == "hr":
                # HR sees only their own history
                print(f"HR '{current_user.username}' accessing own history")
                query = query.filter(MatchingHistory.user_id == current_user.id)
        else:
            # Guest sees only own guest records
            query = query.filter(MatchingHistory.user_id == None)
        
        history_records = query.order_by(
            MatchingHistory.completed_at.desc()
        ).all()
        
        return {
            "status": "success",
            "total_records": len(history_records),
            "current_user": current_user.username if current_user else "Guest",
            "user_role": current_user.role if current_user else "guest",
            "is_admin": current_user.role == "admin" if current_user else False,
            "history": [record.to_dict() for record in history_records]
        }
    
    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/details/{session_id}")
async def get_history_details(
    session_id: str, 
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Get detailed history with permission check"""
    try:
        from ..api.user_routes import get_current_user_from_session
        current_user = get_current_user_from_session(session_token, db)
        
        history_record = db.query(MatchingHistory).filter(
            MatchingHistory.session_id == session_id
        ).first()
        
        if not history_record:
            raise HTTPException(status_code=404, detail="History not found")
        
        # Permission check
        if current_user:
            if current_user.role == "hr" and history_record.user_id != current_user.id:
                raise HTTPException(
                    status_code=403, 
                    detail="Access denied. You can only view your own history."
                )
        else:
            if history_record.user_id is not None:
                raise HTTPException(status_code=403, detail="Access denied")
        
        results = db.query(MatchingResult).filter(
            MatchingResult.session_id == session_id
        ).order_by(MatchingResult.overall_score.desc()).all()
        
        detailed_results = []
        for result in results:
            resume = db.query(Resume).filter(Resume.id == result.resume_id).first()
            if resume:
                resume_data = resume.structured_data or {}
                detailed_results.append({
                    'rank': result.rank_position,
                    'resume_id': result.resume_id,
                    'filename': resume.filename,
                    'candidate_name': resume_data.get('name', 'Unknown'),
                    'overall_score': round(result.overall_score, 2)
                })
        
        return {
            "status": "success",
            "history_info": history_record.to_dict(),
            "detailed_results": detailed_results
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_user_stats(
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Get statistics - admin sees all, HR sees own"""
    try:
        from ..api.user_routes import get_current_user_from_session
        current_user = get_current_user_from_session(session_token, db)
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if current_user.role == "admin":
            # Admin sees ALL users' numeric results
            all_history = db.query(MatchingHistory).all()
            user_stats = {}
            
            for record in all_history:
                user_name = record.user_name or "Guest"
                if user_name not in user_stats:
                    user_stats[user_name] = {
                        "total_sessions": 0,
                        "total_resumes": 0,
                        "total_matches": 0
                    }
                
                user_stats[user_name]["total_sessions"] += 1
                user_stats[user_name]["total_resumes"] += record.total_resumes
                user_stats[user_name]["total_matches"] += record.successful_matches
            
            return {
                "status": "success",
                "user": current_user.username,
                "role": "admin",
                "all_users_stats": user_stats,
                "total_sessions": len(all_history)
            }
        
        elif current_user.role == "hr":
            # HR sees only THEIR numeric results
            history_records = db.query(MatchingHistory).filter(
                MatchingHistory.user_id == current_user.id
            ).all()
            
            total_sessions = len(history_records)
            total_resumes = sum(h.total_resumes for h in history_records)
            total_matches = sum(h.successful_matches for h in history_records)
            
            # ✅ COMPLETE RETURN STATEMENT
            return {
                "status": "success",
                "user": current_user.username,
                "role": "hr",
                "stats": {
                    "total_sessions": total_sessions,
                    "total_resumes_processed": total_resumes,
                    "total_successful_matches": total_matches,
                    "average_success_rate": round(
                        (total_matches / total_resumes * 100) if total_resumes > 0 else 0, 2
                    )
                }
            }
        
        # ✅ ADD FALLBACK FOR OTHER ROLES
        else:
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to view statistics"
            )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{session_id}")
async def delete_history_record(
    session_id: str,
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(None)
):
    """Delete a history record with permission check"""
    try:
        from ..api.user_routes import get_current_user_from_session
        current_user = get_current_user_from_session(session_token, db)
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        history_record = db.query(MatchingHistory).filter(
            MatchingHistory.session_id == session_id
        ).first()
        
        if not history_record:
            raise HTTPException(status_code=404, detail="History not found")
        
        # Permission check: Only admin or record owner can delete
        if current_user.role != "admin" and history_record.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own history records"
            )
        
        db.delete(history_record)
        db.commit()
        
        return {
            "status": "success",
            "message": "History record deleted successfully"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
