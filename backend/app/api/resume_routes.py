import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.resume_models import Resume
from ..services.llm_service import LLMService
from ..services.pdf_processor import PDFProcessor

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


MAX_RESUMES_PER_UPLOAD = 500


@router.post("/upload/{session_id}")
async def upload_resumes(
    session_id: str, files: List[UploadFile] = File(...), db: Session = Depends(get_db)
):
    if len(files) > MAX_RESUMES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_RESUMES_PER_UPLOAD} resumes per upload.",
        )

    processed_resumes = []
    skipped_duplicates = []
    failed_resumes = []
    pdf_processor = PDFProcessor()
    llm_service = LLMService()

    print(f"\n{'=' * 60}")
    print(f"🚀 BATCH UPLOAD STARTED: {len(files)} resumes")
    print(f"Session ID: {session_id}")
    print(f"{'=' * 60}\n")

    # Get existing resumes from database
    existing_resumes = db.query(Resume).filter(Resume.session_id == session_id).all()

    def super_normalize(filename: str) -> str:
        """Ultra-aggressive normalization for duplicate detection"""
        import re

        name = filename.lower().strip()
        if name.endswith(".pdf"):
            name = name[:-4]
        name = re.sub(r"[^\w]", "", name)
        return name

    existing_filenames = {
        super_normalize(resume.filename): resume.filename for resume in existing_resumes
    }

    print(f"📋 Found {len(existing_filenames)} existing resumes in session")

    # Track filenames in current upload
    current_batch_filenames = set()

    # Process in batches with multithreading
    BATCH_SIZE = 10
    MAX_WORKERS = 4  # Number of threads for parallel processing
    total_batches = (len(files) + BATCH_SIZE - 1) // BATCH_SIZE

    # Thread-safe locks
    db_lock = Lock()
    tracking_lock = Lock()

    def process_single_resume_with_content(file_with_content):
        """Process a single resume file with pre-read content"""
        file, file_idx, content = file_with_content
        try:
            original_filename = file.filename
            normalized_filename = super_normalize(original_filename)

            # Thread-safe duplicate checks
            with tracking_lock:
                # CHECK 1: Already exists in database?
                if normalized_filename in existing_filenames:
                    existing_name = existing_filenames[normalized_filename]
                    print(
                        f"⚠️ DUPLICATE (DB): {original_filename} matches '{existing_name}' - SKIPPING"
                    )
                    return {
                        "type": "duplicate",
                        "filename": original_filename,
                        "matched_existing": existing_name,
                        "reason": "Already uploaded in this session (database)",
                        "status": "skipped",
                    }

                # CHECK 2: Already in current batch?
                if normalized_filename in current_batch_filenames:
                    print(f"⚠️ DUPLICATE (BATCH): {original_filename} - SKIPPING")
                    return {
                        "type": "duplicate",
                        "filename": original_filename,
                        "reason": "Duplicate in current upload batch",
                        "status": "skipped",
                    }

                # Add to tracking BEFORE processing
                current_batch_filenames.add(normalized_filename)
                existing_filenames[normalized_filename] = original_filename

            # Save file (thread-safe file operations)
            file_path = f"./data/uploads/resumes/{session_id}_{original_filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(content)

            # Extract and process (CPU-bound operations)
            resume_text = pdf_processor.extract_text_from_pdf(file_path)

            # Run async LLM call in thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                structured_data = loop.run_until_complete(
                    llm_service.extract_resume_information(resume_text)
                )
            finally:
                loop.close()

            # Normalize skills
            if "skills" in structured_data:
                if isinstance(structured_data["skills"], dict):
                    structured_data["skills"] = list(structured_data["skills"].values())
                elif isinstance(structured_data["skills"], str):
                    structured_data["skills"] = [
                        s.strip() for s in structured_data["skills"].split(",")
                    ]
                elif not isinstance(structured_data["skills"], list):
                    structured_data["skills"] = []
            else:
                structured_data["skills"] = []

            # Create resume object
            resume = Resume(
                filename=original_filename,
                file_path=file_path,
                extracted_text=resume_text,
                structured_data=structured_data,
                skills_extracted=structured_data.get("skills", []),
                experience_years=structured_data.get("total_experience", 0),
                session_id=session_id,
            )

            print(f"✅ PROCESSED: {original_filename}")

            return {
                "type": "success",
                "resume_obj": resume,
                "structured_data": structured_data,
                "filename": original_filename,
                "normalized": normalized_filename,
            }

        except Exception as e:
            print(f"❌ ERROR: {file.filename} - {str(e)}")

            # Thread-safe cleanup of tracking
            with tracking_lock:
                if (
                    "normalized_filename" in locals()
                    and normalized_filename in current_batch_filenames
                ):
                    current_batch_filenames.remove(normalized_filename)
                if (
                    "normalized_filename" in locals()
                    and normalized_filename in existing_filenames
                ):
                    del existing_filenames[normalized_filename]

            return {
                "type": "error",
                "filename": file.filename,
                "processing_status": "failed",
                "error": str(e),
            }

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min((batch_num + 1) * BATCH_SIZE, len(files))
        batch_files = files[batch_start:batch_end]

        print(
            f"\n📦 Processing Batch {batch_num + 1}/{total_batches} ({len(batch_files)} resumes)..."
        )

        # Process files in parallel using ThreadPoolExecutor
        batch_resumes_to_add = []
        batch_skipped_duplicates = []
        batch_failed_resumes = []

        # Read all file contents first to avoid async issues in threads
        file_data_list = []
        for idx, file in enumerate(batch_files):
            try:
                content = await file.read()
                file_data_list.append((file, idx, content))
            except Exception as e:
                print(f"❌ ERROR reading {file.filename}: {str(e)}")
                failed_resumes.append(
                    {
                        "filename": file.filename,
                        "processing_status": "failed",
                        "error": f"File read failed: {str(e)}",
                    }
                )

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all files in batch for parallel processing
            future_to_file = {
                executor.submit(
                    process_single_resume_with_content, file_data
                ): file_data[0]
                for file_data in file_data_list
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                try:
                    result = future.result()

                    if result["type"] == "success":
                        batch_resumes_to_add.append(result)
                    elif result["type"] == "duplicate":
                        batch_skipped_duplicates.append(result)
                    elif result["type"] == "error":
                        batch_failed_resumes.append(result)
                except Exception as e:
                    # Handle future execution errors
                    original_file = future_to_file[future]
                    print(f"❌ THREAD ERROR for {original_file.filename}: {str(e)}")
                    batch_failed_resumes.append(
                        {
                            "filename": original_file.filename,
                            "processing_status": "failed",
                            "error": f"Thread execution error: {str(e)}",
                        }
                    )

        # Extend main lists with batch results
        skipped_duplicates.extend(batch_skipped_duplicates)
        failed_resumes.extend(batch_failed_resumes)

        # COMMIT ALL RESUMES IN BATCH AT ONCE (thread-safe database operations)
        if batch_resumes_to_add:
            try:
                with db_lock:
                    for item in batch_resumes_to_add:
                        db.add(item["resume_obj"])

                    db.commit()  # Single commit for entire batch

                    # Refresh and add to processed list
                    for item in batch_resumes_to_add:
                        db.refresh(item["resume_obj"])
                        processed_resumes.append(
                            {
                                "id": item["resume_obj"].id,
                                "filename": item["filename"],
                                "structured_data": item["structured_data"],
                                "processing_status": "success",
                            }
                        )

                print(
                    f"✅ Batch {batch_num + 1} committed ({len(batch_resumes_to_add)} resumes)"
                )

            except Exception as e:
                print(f"❌ Batch commit error: {e}")

                with db_lock:
                    db.rollback()

                # Mark all batch items as failed and remove from tracking
                with tracking_lock:
                    for item in batch_resumes_to_add:
                        failed_resumes.append(
                            {
                                "filename": item["filename"],
                                "processing_status": "failed",
                                "error": f"Batch commit failed: {str(e)}",
                            }
                        )

                        if item["normalized"] in current_batch_filenames:
                            current_batch_filenames.remove(item["normalized"])
                        if item["normalized"] in existing_filenames:
                            del existing_filenames[item["normalized"]]

    print(f"\n{'=' * 60}")
    print("📊 UPLOAD SUMMARY:")
    print(f"   Total Files Uploaded: {len(files)}")
    print(f"   ✅ Successfully Processed: {len(processed_resumes)}")
    print(f"   ⚠️  Duplicates Skipped: {len(skipped_duplicates)}")
    print(f"   ❌ Failed: {len(failed_resumes)}")
    print(f"{'=' * 60}\n")

    return {
        "session_id": session_id,
        "total_uploaded": len(files),
        "successfully_processed": len(processed_resumes),
        "skipped_count": len(skipped_duplicates),
        "failed_count": len(failed_resumes),
        "skipped_files": skipped_duplicates,
        "failed_files": failed_resumes,
        "resumes": processed_resumes,
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
                "experience_years": resume.experience_years,
            }
            for resume in resumes
        ],
    }
