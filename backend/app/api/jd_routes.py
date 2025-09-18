from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
import os
import json

from ..models.database import get_db
from ..models.jd_models import JobDescription, JDStructuringSession
from ..services.llm_service import LLMService
from ..services.pdf_processor import PDFProcessor


router = APIRouter(prefix="/api/jd", tags=["Job Description"])

@router.post("/upload")
async def upload_jd(
    file: UploadFile = File(None),
    text: str = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process job description"""
    session_id = str(uuid.uuid4())
    
    try:
        if file:
            # Handle file upload
            file_path = f"./data/uploads/jds/{session_id}_{file.filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Extract text from PDF
            pdf_processor = PDFProcessor()
            jd_text = pdf_processor.extract_text_from_pdf(file_path)
        elif text:
            jd_text = text
        else:
            raise HTTPException(status_code=400, detail="Either file or text must be provided")
        
        # Create JD record
        jd = JobDescription(
            original_text=jd_text,
            session_id=session_id,
            is_structured=False
        )
        db.add(jd)
        db.commit()
        db.refresh(jd)
        
        # Check if JD needs structuring
        llm_service = LLMService()
        structured_data = await llm_service.structure_job_description(jd_text)
        
        # Create structuring session
        structuring_session = JDStructuringSession(
            session_id=session_id,
            jd_id=jd.id,
            current_structure=structured_data
        )
        db.add(structuring_session)
        db.commit()
        
        return {
            "session_id": session_id,
            "jd_id": jd.id,
            "structured_data": structured_data,
            "needs_approval": True
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve-structure/{session_id}")
async def approve_structure(
    session_id: str,
    approval_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Approve or request changes to structured JD"""
    
    structuring_session = db.query(JDStructuringSession).filter(
        JDStructuringSession.session_id == session_id
    ).first()
    
    if not structuring_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if approval_data.get("approved", False):
        # User approved the structure
        jd = db.query(JobDescription).filter(JobDescription.id == structuring_session.jd_id).first()
        jd.structured_data = structuring_session.current_structure
        jd.is_structured = True
        jd.is_approved = True
        
        structuring_session.is_completed = True
        
        db.commit()
        
        return {
            "status": "approved",
            "message": "JD structure approved successfully",
            "ready_for_skills_weightage": True
        }
    
    else:
        # User wants changes
        feedback = approval_data.get("feedback", "")
        
        llm_service = LLMService()
        refined_structure = await llm_service.refine_structure_based_on_feedback(
            structuring_session.current_structure, feedback
        )
        
        structuring_session.current_structure = refined_structure
        structuring_session.user_feedback = feedback
        structuring_session.revision_count += 1
        
        db.commit()
        
        return {
            "status": "revised",
            "revised_structure": refined_structure,
            "revision_count": structuring_session.revision_count
        }

@router.post("/set-skills-weightage/{session_id}")
async def set_skills_weightage(
    session_id: str,
    skills_data: Dict[str, int],
    db: Session = Depends(get_db)
):
    """Set skills weightage for the JD"""
    
    jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    jd.skills_weightage = skills_data
    db.commit()
    
    return {
        "status": "success",
        "message": "Skills weightage set successfully",
        "ready_for_resume_upload": True
    }

@router.get("/session/{session_id}")
async def get_jd_session(session_id: str, db: Session = Depends(get_db)):
    """Get JD session details"""
    
    jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Session not found")
    
    structuring_session = db.query(JDStructuringSession).filter(
        JDStructuringSession.session_id == session_id
    ).first()
    
    return {
        "jd_data": {
            "id": jd.id,
            "original_text": jd.original_text,
            "structured_data": jd.structured_data,
            "skills_weightage": jd.skills_weightage,
            "is_structured": jd.is_structured,
            "is_approved": jd.is_approved
        },
        "structuring_session": {
            "current_structure": structuring_session.current_structure if structuring_session else None,
            "revision_count": structuring_session.revision_count if structuring_session else 0,
            "is_completed": structuring_session.is_completed if structuring_session else False
        }
    }
