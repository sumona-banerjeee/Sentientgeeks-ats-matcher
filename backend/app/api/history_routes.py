from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..models.database import get_db
from ..models.resume_models import MatchingResult, Resume
from ..models.jd_models import JobDescription
from ..models.history_models import MatchingHistory
from datetime import datetime

router = APIRouter(prefix="/api/history", tags=["History"])

@router.post("/save/{session_id}")
async def save_matching_history(session_id: str, db: Session = Depends(get_db)):
    """Save matching session to history"""
    try:
        # Get job description and matching results
        jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
        results = db.query(MatchingResult).filter(
            MatchingResult.session_id == session_id
        ).order_by(MatchingResult.overall_score.desc()).all()
        
        if not jd or not results:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        # Extract job info
        jd_data = jd.structured_data or {}
        job_title = jd_data.get('job_title', 'Unknown Position')
        company_name = jd_data.get('company', 'Unknown Company')
        
        # Get top candidate info
        top_result = results[0]
        top_resume = db.query(Resume).filter(Resume.id == top_result.resume_id).first()
        top_candidate_name = "Unknown Candidate"
        if top_resume and top_resume.structured_data:
            top_candidate_name = top_resume.structured_data.get('name', top_resume.filename.replace('.pdf', ''))
        
        # Create history record
        history_record = MatchingHistory(
            session_id=session_id,
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
        
        return {"status": "success", "message": "History saved successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving history: {str(e)}")

@router.get("/list")
async def get_matching_history(db: Session = Depends(get_db)):
    """Get all matching history records"""
    try:
        history_records = db.query(MatchingHistory).order_by(
            MatchingHistory.completed_at.desc()
        ).limit(50).all()
        
        return {
            "status": "success",
            "total_records": len(history_records),
            "history": [record.to_dict() for record in history_records]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@router.get("/details/{session_id}")
async def get_history_details(session_id: str, db: Session = Depends(get_db)):
    """Get detailed history for a specific session"""
    try:
        history_record = db.query(MatchingHistory).filter(
            MatchingHistory.session_id == session_id
        ).first()
        
        if not history_record:
            raise HTTPException(status_code=404, detail="History record not found")
        
        # Get full matching results
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching details: {str(e)}")