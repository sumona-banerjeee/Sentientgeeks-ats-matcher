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
    processed_resumes = []
    skipped_duplicates = []
    pdf_processor = PDFProcessor()
    llm_service = LLMService()
    
    for file in files:
        try:
            # CHECK FOR DUPLICATES BY FILENAME
            existing_resume = db.query(Resume).filter(
                Resume.session_id == session_id,
                Resume.filename == file.filename
            ).first()
            
            if existing_resume:
                print(f"DUPLICATE DETECTED: {file.filename} - SKIPPING")
                skipped_duplicates.append({
                    "filename": file.filename,
                    "reason": "Already uploaded in this session"
                })
                continue  # SKIP THIS FILE
            
            # Rest of your code...
            file_path = f"./data/uploads/resumes/{session_id}_{file.filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            resume_text = pdf_processor.extract_text_from_pdf(file_path)
            structured_data = await llm_service.extract_resume_information(resume_text)
            
            # Normalize skills to array
            if 'skills' in structured_data:
                if isinstance(structured_data['skills'], dict):
                    structured_data['skills'] = list(structured_data['skills'].values())
                elif isinstance(structured_data['skills'], str):
                    structured_data['skills'] = [s.strip() for s in structured_data['skills'].split(',')]
                elif not isinstance(structured_data['skills'], list):
                    structured_data['skills'] = []
            else:
                structured_data['skills'] = []
            
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
            print(f"Error processing {file.filename}: {str(e)}")
            processed_resumes.append({
                "filename": file.filename,
                "processing_status": "failed",
                "error": str(e)
            })
    
    return {
        "session_id": session_id,
        "total_uploaded": len(files),
        "successfully_processed": len([r for r in processed_resumes if r.get("processing_status") == "success"]),
        "skipped_count": len(skipped_duplicates),
        "skipped_files": skipped_duplicates,
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