from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..models.database import get_db
from ..models.jd_models import JobDescription
from ..services.interview_service import InterviewService

router = APIRouter(prefix="/api/interview", tags=["Interview"])

@router.post("/generate-questions/{session_id}")
async def generate_interview_questions(
    session_id: str, 
    regenerate: bool = False,
    db: Session = Depends(get_db)
):
    #Generate interview questions based on JD for the session
    
    # Getting the JD data
    jd = db.query(JobDescription).filter(
        JobDescription.session_id == session_id
    ).first()


    
    if not jd:
        raise HTTPException(
            status_code=404, 
            detail="No approved job description found for this session"
        )
    
    if not jd.structured_data:
        raise HTTPException(
            status_code=400,
            detail="Job description data is not properly structured"
        )
    
    try:
        interview_service = InterviewService()
        questions = await interview_service.generate_interview_questions(jd.structured_data)
        
        if not questions or len(questions) < 5:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate sufficient interview questions"
            )
        
        # Getting info for job info for peroviding response
        job_info = {
            "job_title": jd.structured_data.get('job_title', 'Unknown Position'),
            "company": jd.structured_data.get('company', 'Company'),
            "primary_skills": jd.structured_data.get('primary_skills', []),
            "secondary_skills": jd.structured_data.get('secondary_skills', []),
            "experience_required": jd.structured_data.get('experience_required', 'Not specified')
        }
        
        return {
            "session_id": session_id,
            "job_info": job_info,
            "questions": questions,
            "total_questions": len(questions),
            "difficulty_level": "Medium to Hard",
            "regenerated": regenerate
        }
        
    except Exception as e:
        print(f"Error generating interview questions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate interview questions: {str(e)}"
        )

@router.get("/questions/{session_id}")
async def get_cached_questions(session_id: str, db: Session = Depends(get_db)):
    """Get previously generated questions if available"""
    # This could be extended to cache questions in database, at this moment it will trigger regeneration
    return await generate_interview_questions(session_id, regenerate=False, db=db)
