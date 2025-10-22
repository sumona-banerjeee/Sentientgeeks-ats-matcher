from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from ..models.database import get_db
from ..models.resume_models import Resume
from ..services.pdf_processor import PDFProcessor
from ..services.llm_service import LLMService


router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


MAX_RESUMES_PER_UPLOAD = 500

@router.post("/upload/{session_id}")
async def upload_resumes(
    session_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if len(files) > MAX_RESUMES_PER_UPLOAD:
        raise HTTPException(
            status_code=400, 
            detail=f"Too many files. Maximum {MAX_RESUMES_PER_UPLOAD} resumes per upload."
        )
    
    processed_resumes = []
    skipped_duplicates = []
    failed_resumes = []
    pdf_processor = PDFProcessor()
    llm_service = LLMService()
    
    print(f"\n{'='*60}")
    print(f"🚀 BATCH UPLOAD STARTED: {len(files)} resumes")
    print(f"Session ID: {session_id}")
    print(f"{'='*60}\n")
    
    # CRITICAL FIX: Get ALL existing resumes and normalize filenames
    existing_resumes = db.query(Resume).filter(
        Resume.session_id == session_id
    ).all()
    
    # Create normalized filename set (lowercase + stripped)
    existing_filenames = {
        resume.filename.lower().strip().replace(' ', '_') 
        for resume in existing_resumes
    }
    
    print(f"📋 Found {len(existing_filenames)} existing resumes in session")
    print(f"   Existing files: {list(existing_filenames)[:5]}")
    
    # NEW: Track filenames being processed in current batch
    current_batch_filenames = set()
    
    # Process in batches of 10 for better performance
    BATCH_SIZE = 10
    total_batches = (len(files) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min((batch_num + 1) * BATCH_SIZE, len(files))
        batch_files = files[batch_start:batch_end]
        
        print(f"\n📦 Processing Batch {batch_num + 1}/{total_batches} ({len(batch_files)} resumes)...")
        
        for file in batch_files:
            try:
                # ENHANCED: Normalize filename for comparison
                original_filename = file.filename
                normalized_filename = original_filename.lower().strip().replace(' ', '_')
                
                # CHECK 1: Already exists in database?
                if normalized_filename in existing_filenames:
                    print(f"⚠️  DUPLICATE (DB): {original_filename} - SKIPPING")
                    skipped_duplicates.append({
                        "filename": original_filename,
                        "reason": "Already uploaded in this session (database)",
                        "status": "skipped"
                    })
                    continue
                
                # CHECK 2: Already processed in current batch?
                if normalized_filename in current_batch_filenames:
                    print(f"⚠️  DUPLICATE (BATCH): {original_filename} - SKIPPING")
                    skipped_duplicates.append({
                        "filename": original_filename,
                        "reason": "Duplicate in current upload batch",
                        "status": "skipped"
                    })
                    continue
                
                # CRITICAL: Add to current batch tracker IMMEDIATELY
                current_batch_filenames.add(normalized_filename)
                existing_filenames.add(normalized_filename)  # Also update main set
                
                # Save file with ORIGINAL filename (preserve user's naming)
                file_path = f"./data/uploads/resumes/{session_id}_{original_filename}"
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                # Extract text from PDF
                resume_text = pdf_processor.extract_text_from_pdf(file_path)
                
                # Extract structured data using LLM
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
                
                # Create database record with ORIGINAL filename
                resume = Resume(
                    filename=original_filename,  # Keep original filename for display
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
                
                print(f"✅ SUCCESS: {original_filename}")
                
            except Exception as e:
                print(f"❌ ERROR: {file.filename} - {str(e)}")
                failed_resumes.append({
                    "filename": file.filename,
                    "processing_status": "failed",
                    "error": str(e)
                })
                # Remove from batch tracker if processing failed
                if normalized_filename in current_batch_filenames:
                    current_batch_filenames.remove(normalized_filename)
                    existing_filenames.remove(normalized_filename)
                continue
        
        # Commit batch
        try:
            db.commit()
            print(f"✅ Batch {batch_num + 1} committed to database")
        except Exception as e:
            print(f"❌ Batch commit error: {e}")
            db.rollback()
    
    print(f"\n{'='*60}")
    print(f"📊 UPLOAD SUMMARY:")
    print(f"   Total Files Uploaded: {len(files)}")
    print(f"   ✅ Successfully Processed: {len(processed_resumes)}")
    print(f"   ⚠️  Duplicates Skipped: {len(skipped_duplicates)}")
    print(f"   ❌ Failed: {len(failed_resumes)}")
    print(f"{'='*60}\n")
    
    return {
        "session_id": session_id,
        "total_uploaded": len(files),
        "successfully_processed": len(processed_resumes),
        "skipped_count": len(skipped_duplicates),
        "failed_count": len(failed_resumes),
        "skipped_files": skipped_duplicates,
        "failed_files": failed_resumes,
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