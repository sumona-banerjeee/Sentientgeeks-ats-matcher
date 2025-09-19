from fastapi import APIRouter, HTTPException, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import csv
import json
import io
from ..models.database import get_db
from ..models.history_models import MatchingSession, MatchingHistory, ATSScoreHistory, ExportHistory
from ..models.resume_models import MatchingResult, Resume
from ..models.jd_models import JobDescription
from sqlalchemy import desc, func

router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("/sessions")
async def get_all_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None)
):
    """Get all matching sessions with pagination"""
    query = db.query(MatchingSession)
    
    if status:
        query = query.filter(MatchingSession.status == status)
    
    total = query.count()
    sessions = query.order_by(desc(MatchingSession.last_activity)).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "sessions": [
            {
                "id": s.id,
                "session_id": s.session_id,
                "session_name": s.session_name,
                "jd_title": s.jd_title,
                "total_resumes": s.total_resumes,
                "processed_resumes": s.processed_resumes,
                "status": s.status,
                "created_at": s.created_at,
                "completed_at": s.completed_at,
                "last_activity": s.last_activity
            }
            for s in sessions
        ]
    }

@router.get("/session/{session_id}")
async def get_session_details(session_id: str, db: Session = Depends(get_db)):
    """Get detailed session information"""
    session = db.query(MatchingSession).filter(MatchingSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session history
    history = db.query(MatchingHistory).filter(
        MatchingHistory.session_id == session_id
    ).order_by(desc(MatchingHistory.timestamp)).all()
    
    # Get matching results
    results = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id
    ).order_by(MatchingResult.rank_position).all()
    
    # Get ATS score history
    scores = db.query(ATSScoreHistory).filter(
        ATSScoreHistory.session_id == session_id
    ).order_by(desc(ATSScoreHistory.timestamp)).all()
    
    return {
        "session": {
            "id": session.id,
            "session_id": session.session_id,
            "session_name": session.session_name,
            "jd_title": session.jd_title,
            "total_resumes": session.total_resumes,
            "processed_resumes": session.processed_resumes,
            "status": session.status,
            "created_at": session.created_at,
            "completed_at": session.completed_at,
            "last_activity": session.last_activity
        },
        "history": [
            {
                "id": h.id,
                "action_type": h.action_type,
                "action_description": h.action_description,
                "details": h.details,
                "timestamp": h.timestamp,
                "execution_time": h.execution_time,
                "success": h.success,
                "error_message": h.error_message
            }
            for h in history
        ],
        "results": [
            {
                "id": r.id,
                "resume_id": r.resume_id,
                "overall_score": r.overall_score,
                "skill_match_score": r.skill_match_score,
                "experience_score": r.experience_score,
                "rank_position": r.rank_position,
                "created_at": r.created_at,
                "detailed_analysis": r.detailed_analysis
            }
            for r in results
        ],
        "score_history": [
            {
                "id": s.id,
                "resume_id": s.resume_id,
                "overall_score": s.overall_score,
                "skill_match_score": s.skill_match_score,
                "experience_score": s.experience_score,
                "detailed_breakdown": s.detailed_breakdown,
                "timestamp": s.timestamp
            }
            for s in scores
        ]
    }

@router.post("/session/{session_id}/log")
async def log_action(
    session_id: str,
    action_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Log an action to session history"""
    
    # Ensure session exists
    session = db.query(MatchingSession).filter(MatchingSession.session_id == session_id).first()
    if not session:
        # Create new session
        session = MatchingSession(
            session_id=session_id,
            session_name=action_data.get("session_name", f"Session {session_id[:8]}"),
            status="active"
        )
        db.add(session)
        db.commit()
    
    # Update last activity
    session.last_activity = datetime.utcnow()
    
    # Create history entry
    history = MatchingHistory(
        session_id=session_id,
        action_type=action_data.get("action_type", "unknown"),
        action_description=action_data.get("description", ""),
        details=action_data.get("details", {}),
        execution_time=action_data.get("execution_time"),
        success=action_data.get("success", True),
        error_message=action_data.get("error_message")
    )
    
    db.add(history)
    db.commit()
    
    return {"status": "success", "message": "Action logged"}

@router.post("/session/{session_id}/score")
async def log_ats_score(
    session_id: str,
    score_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Log ATS score to history"""
    
    score_history = ATSScoreHistory(
        session_id=session_id,
        resume_id=score_data.get("resume_id"),
        jd_id=score_data.get("jd_id"),
        overall_score=score_data.get("overall_score"),
        skill_match_score=score_data.get("skill_match_score"),
        experience_score=score_data.get("experience_score"),
        education_score=score_data.get("education_score"),
        keyword_match_score=score_data.get("keyword_match_score"),
        detailed_breakdown=score_data.get("detailed_breakdown", {}),
        matching_algorithm_version=score_data.get("algorithm_version", "v1.0")
    )
    
    db.add(score_history)
    db.commit()
    
    return {"status": "success", "message": "Score logged"}

@router.get("/session/{session_id}/export/{format}")
async def export_session_data(
    session_id: str,
    format: str,
    db: Session = Depends(get_db)
):
    """Export session data in JSON or CSV format"""
    
    session = db.query(MatchingSession).filter(MatchingSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all data
    results = db.query(MatchingResult).join(Resume).filter(
        MatchingResult.session_id == session_id
    ).all()
    
    if format.lower() == "json":
        export_data = {
            "session": {
                "session_id": session.session_id,
                "session_name": session.session_name,
                "jd_title": session.jd_title,
                "created_at": session.created_at.isoformat(),
                "total_resumes": session.total_resumes
            },
            "results": [
                {
                    "resume_filename": result.resume.filename,
                    "overall_score": result.overall_score,
                    "skill_match_score": result.skill_match_score,
                    "experience_score": result.experience_score,
                    "rank_position": result.rank_position,
                    "detailed_analysis": result.detailed_analysis,
                    "created_at": result.created_at.isoformat()
                }
                for result in results
            ]
        }
        
        # Log export
        export_log = ExportHistory(
            session_id=session_id,
            export_type="json",
            file_name=f"{session_id}_results.json",
            export_data={"record_count": len(results)}
        )
        db.add(export_log)
        db.commit()
        
        return Response(
            content=json.dumps(export_data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={session_id}_results.json"}
        )
    
    elif format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            "Resume Filename", "Overall Score", "Skill Match Score", 
            "Experience Score", "Rank Position", "Created At"
        ])
        
        # Write data
        for result in results:
            writer.writerow([
                result.resume.filename,
                result.overall_score,
                result.skill_match_score,
                result.experience_score,
                result.rank_position,
                result.created_at.isoformat()
            ])
        
        # Log export
        export_log = ExportHistory(
            session_id=session_id,
            export_type="csv",
            file_name=f"{session_id}_results.csv",
            export_data={"record_count": len(results)}
        )
        db.add(export_log)
        db.commit()
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={session_id}_results.csv"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a complete session and all its data"""
    
    session = db.query(MatchingSession).filter(MatchingSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete all related data (cascade will handle this)
    db.delete(session)
    db.commit()
    
    return {"status": "success", "message": f"Session {session_id} deleted successfully"}

@router.delete("/session/{session_id}/history")
async def delete_session_history(session_id: str, db: Session = Depends(get_db)):
    """Delete only the history of a session, keep results"""
    
    deleted_count = db.query(MatchingHistory).filter(
        MatchingHistory.session_id == session_id
    ).delete()
    
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Deleted {deleted_count} history records for session {session_id}"
    }

@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get analytics data"""
    
    # Total sessions
    total_sessions = db.query(MatchingSession).count()
    
    # Active sessions
    active_sessions = db.query(MatchingSession).filter(MatchingSession.status == "active").count()
    
    # Total resumes processed
    total_resumes = db.query(func.sum(MatchingSession.processed_resumes)).scalar() or 0
    
    # Average scores
    avg_scores = db.query(
        func.avg(MatchingResult.overall_score),
        func.avg(MatchingResult.skill_match_score),
        func.avg(MatchingResult.experience_score)
    ).first()
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = db.query(MatchingSession).filter(
        MatchingSession.created_at >= week_ago
    ).count()
    
    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_resumes_processed": int(total_resumes),
        "average_scores": {
            "overall": float(avg_scores[0]) if avg_scores[0] else 0,
            "skill_match": float(avg_scores[1]) if avg_scores[1] else 0,
            "experience": float(avg_scores[2]) if avg_scores[2] else 0
        },
        "recent_activity": {
            "sessions_last_7_days": recent_sessions
        }
    }
