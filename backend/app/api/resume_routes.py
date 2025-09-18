from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import uuid

from ..models.database import get_db
from ..models.resume_models import Resume
from ..services.pdf_processor import PDFProcessor
from ..services.llm_service import LLMService


router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

@router.post("/upload/{session_id}")
async def upload_resumes(
    session_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process multiple resumes"""
    
    processed_resumes = []
    pdf_processor = PDFProcessor()
    llm_service = LLMService()
    
    for file in files:
        try:
            # Save file
            file_path = f"./data/uploads/resumes/{session_id}_{file.filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Extract text
            resume_text = pdf_processor.extract_text_from_pdf(file_path)
            
            # Extract structured information
            structured_data = await llm_service.extract_resume_information(resume_text)
            
            # Create resume record
            resume = Resume(
                filename=file.filename,
                file_path=file_path,
                extracted_text=resume_text,
                structured_data=structured_data,
                skills_extracted=structured_data.get('skills', []),
                experience_years=structured_data.get('total_experience', 0),
                session_id=session_id
            )
            
            db.add(resume)
            db.commit()
            db.refresh(resume)
            
            processed_resumes.append({
                "id": resume.id,
                "filename": resume.filename,
                "structured_data": structured_data,
                "processing_status": "success"
            })
            
        except Exception as e:
            processed_resumes.append({
                "filename": file.filename,
                "processing_status": "failed",
                "error": str(e)
            })
    
    return {
        "session_id": session_id,
        "total_uploaded": len(files),
        "successfully_processed": len([r for r in processed_resumes if r.get("processing_status") == "success"]),
        "resumes": processed_resumes
    }

@router.get("/session/{session_id}")
async def get_resumes_by_session(session_id: str, db: Session = Depends(get_db)):
    """Get all resumes for a session"""
    
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    
    return {
        "session_id": session_id,
        "total_resumes": len(resumes),
        "resumes": [
            {
                "id": resume.id,
                "filename": resume.filename,
                "structured_data": resume.structured_data,
                "skills_extracted": resume.skills_extracted,
                "experience_years": resume.experience_years
            }
            for resume in resumes
        ]
    }
