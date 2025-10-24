from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass
import time

from ..models.database import get_db
from ..models.jd_models import JobDescription
from ..models.resume_models import Resume, MatchingResult
from ..services.matching_engine import MatchingEngine

# Importing the Agentic AI Service
try:
    from ..services.agentic_service import (
        EnhancedAgenticATSService as AgenticATSService,
    )

    AGENTIC_AVAILABLE = True
    print("Agentic AI Service available")
except ImportError:
    AGENTIC_AVAILABLE = False
    print("Agentic AI Service not available - using traditional matching")

router = APIRouter(prefix="/api/matching", tags=["Matching"])

# Checking if the Agentic AI should be used
USE_AGENTIC_AI = (
    os.getenv("USE_AGENTIC_AI", "false").lower() == "true" and AGENTIC_AVAILABLE
)

# Initializing the services
matching_engine = MatchingEngine()
if USE_AGENTIC_AI:
    try:
        agentic_service = AgenticATSService()
        print("Initialized Agentic AI Service for matching")
    except Exception as e:
        print(f"Failed to initialize Agentic AI: {e}")
        USE_AGENTIC_AI = False
        agentic_service = None
else:
    agentic_service = None
    print("Using traditional matching engine")


@dataclass
class ResumeProcessingResult:
    resume_id: int
    filename: str
    candidate_name: str
    ats_score: dict = None
    error: str = None
    processing_time: float = 0.0


class RateLimiter:
    """Thread-safe rate limiter for API calls"""

    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            # Remove old calls outside the time window
            self.calls = [
                call_time
                for call_time in self.calls
                if now - call_time < self.time_window
            ]

            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = min(self.calls)
                wait_time = self.time_window - (now - oldest_call)
                if wait_time > 0:
                    time.sleep(wait_time)
                    now = time.time()

            self.calls.append(now)


def process_single_resume(
    resume: Resume,
    jd_data: dict,
    skills_weightage: dict,
    jd_id: int,
    session_id: str,
    rate_limiter: RateLimiter = None,
) -> ResumeProcessingResult:
    """Process a single resume with thread-safe operations"""
    start_time = time.time()

    try:
        # Apply rate limiting if provided
        if rate_limiter:
            rate_limiter.acquire()

        print(f"🔄 Processing resume: {resume.filename}")

        # Ensure valid structured data
        resume_data = resume.structured_data if resume.structured_data else {}

        print(
            f"📊 Resume data keys: {list(resume_data.keys()) if resume_data else 'None'}"
        )

        # Initialize scores
        overall_score = 0
        skills_score = 0
        experience_score = 0
        detailed_analysis = {}
        scoring_method = "Traditional"

        # Create local instances for thread safety
        local_matching_engine = MatchingEngine()
        local_agentic_service = None

        if USE_AGENTIC_AI:
            try:
                # Import and create agentic service locally for thread safety
                from ..services.agentic_service import EnhancedAgenticATSService

                local_agentic_service = EnhancedAgenticATSService()

                print("🤖 Using Agentic AI for comprehensive scoring...")

                # Run async function in thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                agentic_result = loop.run_until_complete(
                    local_agentic_service.match_and_score(
                        resume_data=resume_data, jd_data=jd_data
                    )
                )
                loop.close()

                print(f"Agentic AI Result processed")

                # Extract scores from agentic result
                overall_score = float(
                    agentic_result.get("overallscore")
                    or agentic_result.get("overall_score")
                    or 0
                )

                skills_score = float(
                    agentic_result.get("skillmatchscore")
                    or agentic_result.get("skill_match_score")
                    or agentic_result.get("skillMatchScore")
                    or 0
                )

                experience_score = float(
                    agentic_result.get("experiencescore")
                    or agentic_result.get("experience_match_score")
                    or agentic_result.get("experience_score")
                    or agentic_result.get("experienceScore")
                    or 0
                )
                detailed_analysis = agentic_result.get("detailed_analysis", {})

                # Add agentic-specific data to analysis
                detailed_analysis["scoring_method"] = "Agentic AI"
                detailed_analysis["recommendation"] = agentic_result.get(
                    "recommendation", "Unknown"
                )
                detailed_analysis["matched_skills"] = agentic_result.get(
                    "matched_skills", []
                )
                detailed_analysis["missing_skills"] = agentic_result.get(
                    "missing_skills", []
                )
                scoring_method = "Agentic AI"

                print(
                    f"Agentic Scores - Overall: {overall_score}%, Skills: {skills_score}%, Experience: {experience_score}%"
                )

            except Exception as agentic_error:
                print(f"Agentic AI failed: {str(agentic_error)}")
                print(f"Falling back to traditional matching engine...")
                scoring_method = "Traditional (Agentic Fallback)"

        # Use traditional matching if agentic failed or not enabled
        if overall_score == 0 and skills_score == 0 and experience_score == 0:
            print("Using traditional matching engine...")

            # Calculate ATS score using traditional method
            ats_score = local_matching_engine.calculate_ats_score(
                jd_data, resume_data, skills_weightage
            )

            overall_score = ats_score.get("overall_score", 0)
            detailed_analysis = ats_score.get("detailed_analysis", {})
            detailed_analysis["scoring_method"] = scoring_method

            # Calculate individual scores
            skills_score, experience_score = _calculate_traditional_scores(
                jd_data, resume_data, skills_weightage, ats_score
            )

        processing_time = time.time() - start_time

        print(f"✅ Successfully processed: {resume.filename} in {processing_time:.2f}s")

        return ResumeProcessingResult(
            resume_id=resume.id,
            filename=resume.filename,
            candidate_name=resume_data.get("name", "Unknown")
            if resume_data
            else "Unknown",
            ats_score={
                "overall_score": round(overall_score, 2),
                "skill_match_score": round(skills_score, 2),
                "experience_score": round(experience_score, 2),
                "detailed_analysis": detailed_analysis,
            },
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Error processing {resume.filename}: {str(e)}")
        traceback.print_exc()

        return ResumeProcessingResult(
            resume_id=resume.id,
            filename=resume.filename,
            candidate_name=resume.structured_data.get("name", "Unknown")
            if resume.structured_data
            else "Unknown",
            error=str(e),
            processing_time=processing_time,
        )


@router.post("/start/{session_id}")
async def start_matching(session_id: str, db: Session = Depends(get_db)):
    """Start matching process for all resumes in a session with multithreaded processing"""

    print(f"\n{'=' * 60}")
    print(f"Starting MULTITHREADED matching process for session: {session_id}")
    print(f"Agentic AI Mode: {'ENABLED' if USE_AGENTIC_AI else 'DISABLED'}")
    print(f"{'=' * 60}\n")

    # Get job description
    jd = (
        db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    )
    if not jd or not jd.is_approved:
        raise HTTPException(status_code=400, detail="JD not found or not approved")

    # Extract job title safely
    job_title = "Unknown Job"
    if jd.structured_data and isinstance(jd.structured_data, dict):
        job_title = jd.structured_data.get(
            "job_title", jd.structured_data.get("title", "Unknown Job")
        )

    print(f"Found approved JD: {job_title}")

    # Get all resumes for this session
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    if not resumes:
        raise HTTPException(
            status_code=400,
            detail="No resumes found for this session. Please upload resumes first.",
        )

    print(f"Found {len(resumes)} resumes to process\n")

    # Clear any existing results for this session
    db.query(MatchingResult).filter(MatchingResult.session_id == session_id).delete()
    db.commit()

    # Prepare data for processing
    jd_data = jd.structured_data if jd.structured_data else {}
    skills_weightage = jd.skills_weightage if jd.skills_weightage else {}

    print(f"📊 JD data keys: {list(jd_data.keys()) if jd_data else 'None'}")

    # Configure threading
    max_workers = min(4, len(resumes))  # Limit to 4 threads to avoid overwhelming APIs
    use_rate_limiting = USE_AGENTIC_AI  # Only rate limit if using Agentic AI

    # Create rate limiter if needed (2 calls per 5 seconds for API limits)
    rate_limiter = (
        RateLimiter(max_calls=2, time_window=5.0) if use_rate_limiting else None
    )

    print(f"🚀 Starting multithreaded processing with {max_workers} workers")
    print(f"⏱️ Rate limiting: {'ENABLED' if use_rate_limiting else 'DISABLED'}")

    matching_results = []
    processing_start_time = time.time()

    # Process resumes in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_resume = {
            executor.submit(
                process_single_resume,
                resume,
                jd_data,
                skills_weightage,
                jd.id,
                session_id,
                rate_limiter,
            ): resume
            for resume in resumes
        }

        # Collect results as they complete
        completed_count = 0
        for future in as_completed(future_to_resume):
            resume = future_to_resume[future]
            completed_count += 1

            try:
                result = future.result()
                matching_results.append(result)

                status = "✅ SUCCESS" if result.ats_score else "❌ FAILED"
                print(
                    f"[{completed_count}/{len(resumes)}] {status}: {resume.filename} ({result.processing_time:.2f}s)"
                )

            except Exception as e:
                print(
                    f"[{completed_count}/{len(resumes)}] ❌ EXCEPTION: {resume.filename} - {str(e)}"
                )
                matching_results.append(
                    ResumeProcessingResult(
                        resume_id=resume.id,
                        filename=resume.filename,
                        candidate_name="Unknown",
                        error=str(e),
                    )
                )

    total_processing_time = time.time() - processing_start_time
    print(f"\n🎯 Multithreaded processing completed in {total_processing_time:.2f}s")
    print(f"📈 Average time per resume: {total_processing_time / len(resumes):.2f}s")

    # Save all results to database in batch
    print(f"\n💾 Saving {len(matching_results)} results to database...")
    db_save_start = time.time()

    successful_results = [r for r in matching_results if r.ats_score]

    for result in successful_results:
        matching_result = MatchingResult(
            session_id=session_id,
            jd_id=jd.id,
            resume_id=result.resume_id,
            overall_score=result.ats_score["overall_score"],
            skill_match_score=result.ats_score["skill_match_score"],
            experience_score=result.ats_score["experience_score"],
            detailed_analysis=result.ats_score["detailed_analysis"],
            rank_position=0,  # temporary, updated later
        )
        db.add(matching_result)

    try:
        db.commit()
        db_save_time = time.time() - db_save_start
        print(f"✅ Database save completed in {db_save_time:.2f}s")
    except Exception as e:
        print(f"❌ Error saving results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error saving matching results")

    # RANKING RESUMES BY OVERALL SCORE
    print(f"\n{'=' * 60}")
    print("Ranking candidates...")
    print(f"{'=' * 60}\n")

    # Convert results to ranking format
    ranking_results = []
    for result in matching_results:
        if result.ats_score:
            ranking_results.append(
                {
                    "resume_id": result.resume_id,
                    "filename": result.filename,
                    "candidate_name": result.candidate_name,
                    "ats_score": result.ats_score,
                }
            )

    successful_matches = ranking_results
    successful_matches.sort(key=lambda x: x["ats_score"]["overall_score"], reverse=True)

    # Update rank positions in DB starting from 1.
    for rank, result in enumerate(successful_matches, 1):
        matching_result = (
            db.query(MatchingResult)
            .filter(
                MatchingResult.session_id == session_id,
                MatchingResult.resume_id == result["resume_id"],
            )
            .first()
        )
        if matching_result:
            matching_result.rank_position = rank
            scoring_method = matching_result.detailed_analysis.get(
                "scoring_method", "Unknown"
            )
            print(
                f"Rank #{rank}: {result['filename']} - Score: {result['ats_score']['overall_score']}% [{scoring_method}]"
            )

    # Commit all changes
    try:
        db.commit()
        print(f"\nMatching completed: {len(successful_matches)} successful matches")
        print(f"{'=' * 60}\n")
    except Exception as e:
        print(f"Error saving results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error saving matching results")

    return {
        "session_id": session_id,
        "total_resumes": len(resumes),
        "successfully_matched": len(successful_matches),
        "ranking": successful_matches,
        "agentic_ai_used": USE_AGENTIC_AI,
        "status": "completed",
        "performance_metrics": {
            "total_processing_time": round(total_processing_time, 2),
            "average_processing_time": round(total_processing_time / len(resumes), 2),
            "database_save_time": round(db_save_time, 2)
            if "db_save_time" in locals()
            else 0,
            "threads_used": max_workers,
            "rate_limiting_enabled": use_rate_limiting,
        },
    }


@router.get("/results/{session_id}")
async def get_matching_results(session_id: str, db: Session = Depends(get_db)):
    """Get detailed matching results for a session"""

    print(f"Fetching matching results for session: {session_id}")

    # Atfirst it will check if resumes exist for this session
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    if not resumes:
        print(f"No resumes found for session: {session_id}")
        raise HTTPException(
            status_code=400,
            detail="No resumes found for this session. Please upload resumes first.",
        )

    print(f"Found {len(resumes)} resumes for session {session_id}")

    # Checking if matching results exist ORDER BY overall score DESC for proper ranking
    results = (
        db.query(MatchingResult)
        .filter(MatchingResult.session_id == session_id)
        .order_by(MatchingResult.overall_score.desc())
        .all()
    )

    print(f"Found {len(results)} matching results")

    if not results:
        print(f"No matching results found for session: {session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"No matching results found. Please run the matching process first for the {len(resumes)} uploaded resumes.",
        )

    # Building detailed results with PROPER SCORING
    detailed_results = []
    for rank, result in enumerate(results, 1):
        resume = db.query(Resume).filter(Resume.id == result.resume_id).first()

        if resume:
            resume_data = resume.structured_data if resume.structured_data else {}

            # Ensuring scores are properly formatted and not null
            skill_score = (
                result.skill_match_score if result.skill_match_score is not None else 0
            )
            exp_score = (
                result.experience_score if result.experience_score is not None else 0
            )

            # Getting scoring method from detailed analysis
            scoring_method = (
                result.detailed_analysis.get("scoring_method", "Unknown")
                if result.detailed_analysis
                else "Unknown"
            )

            detailed_results.append(
                {
                    "rank": rank,
                    "resume_id": result.resume_id,
                    "filename": resume.filename,
                    "candidate_name": resume_data.get("name", "Unknown"),
                    "overall_score": round(result.overall_score, 2),
                    "skill_match_score": round(skill_score, 2),
                    "experience_score": round(exp_score, 2),
                    "detailed_analysis": result.detailed_analysis or {},
                    "skills_found": resume_data.get("skills", []),
                    "scoring_method": scoring_method,
                }
            )

    print(f"Returning {len(detailed_results)} detailed results, ranked by score\n")

    return {
        "session_id": session_id,
        "total_results": len(detailed_results),
        "results": detailed_results,
        "agentic_ai_used": USE_AGENTIC_AI,
        "status": "success",
    }


@router.get("/detailed/{session_id}/{resume_id}")
async def get_detailed_analysis(
    session_id: str, resume_id: int, db: Session = Depends(get_db)
):
    # Getting detailed analysis for a specific resume

    print(f"Fetching detailed analysis for resume {resume_id} in session {session_id}")

    result = (
        db.query(MatchingResult)
        .filter(
            MatchingResult.session_id == session_id,
            MatchingResult.resume_id == resume_id,
        )
        .first()
    )

    if not result:
        raise HTTPException(status_code=404, detail="Matching result not found")

    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    jd = (
        db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    )

    if not resume or not jd:
        raise HTTPException(status_code=404, detail="Resume or JD not found")

    # Extracting detailed personal information
    resume_data = resume.structured_data or {}
    jd_data = jd.structured_data or {}

    # Extracting contact information
    personal_info = {
        "name": resume_data.get("name", "Unknown"),
        "email": resume_data.get("email", "Not provided"),
        "phone": resume_data.get("phone", "Not provided"),
        "linkedin": resume_data.get("linkedin", "Not provided"),
        "github": resume_data.get("github", "Not provided"),
        "portfolio": resume_data.get("portfolio", "Not provided"),
        "location": resume_data.get("location", "Not provided"),
    }

    # Extracting professional information
    professional_info = {
        "total_experience": resume_data.get("total_experience", 0),
        "current_role": resume_data.get("current_role", "Not specified"),
        "skills": resume_data.get("skills", []),
        "education": resume_data.get("education", []),
        "certifications": resume_data.get("certifications", []),
        "experience_timeline": resume_data.get("experience_timeline", []),
    }

    # Matching analysis with proper scores
    detailed_analysis = result.detailed_analysis or {}
    skill_score = (
        result.skill_match_score if result.skill_match_score is not None else 0
    )
    exp_score = result.experience_score if result.experience_score is not None else 0
    scoring_method = detailed_analysis.get("scoring_method", "Unknown")

    # Agentic AI specific fields (if available)
    agentic_insights = {}
    if scoring_method == "Agentic AI":
        agentic_insights = {
            "recommendation": detailed_analysis.get("recommendation", "Unknown"),
            "matched_skills": detailed_analysis.get("matched_skills", []),
            "missing_skills": detailed_analysis.get("missing_skills", []),
            "strengths": detailed_analysis.get("strengths", []),
            "weaknesses": detailed_analysis.get("weaknesses", []),
            "key_highlights": detailed_analysis.get("key_highlights", []),
        }

    return {
        "resume_info": {
            "id": resume.id,
            "filename": resume.filename,
            "personal_info": personal_info,
            "professional_info": professional_info,
        },
        "jd_info": {
            "job_title": jd_data.get("job_title", "Unknown"),
            "company": jd_data.get("company", "Unknown"),
            "required_skills": jd_data.get("primary_skills", [])
            + jd_data.get("secondary_skills", []),
            "experience_required": jd_data.get("experience_required", "Not specified"),
        },
        "matching_analysis": {
            "rank": result.rank_position,
            "rank_position": result.rank_position,
            "overall_score": round(result.overall_score, 2),
            "skill_match_score": round(skill_score, 2),
            "experience_score": round(exp_score, 2),
            "detailed_analysis": detailed_analysis,
            "scoring_method": scoring_method,
            "agentic_insights": agentic_insights if agentic_insights else None,
        },
    }


# HELPER FUNCTION FOR TRADITIONAL SCORING


def _calculate_traditional_scores(
    jd_data: dict, resume_data: dict, skills_weightage: dict, ats_score: dict
) -> tuple[float, float]:
    # Calculating individual skill and experience scores using traditional matching engine

    try:
        # Parsing JD experience requirement
        jd_exp_required = 0
        if jd_data.get("experience_required"):
            try:
                jd_exp_required = matching_engine._parse_experience_years(
                    str(jd_data["experience_required"])
                )
            except:
                jd_exp_required = 0

        # Extracting job priorities
        job_priorities = matching_engine._extract_job_priorities(jd_data, None)

        # Calculating individual scores using matching engine methods
        skills_score = matching_engine._calculate_complete_skills_score(
            resume_data, job_priorities, skills_weightage
        )
        experience_score = matching_engine._calculate_enhanced_experience_score(
            resume_data, job_priorities, jd_exp_required
        )

        print(
            f"Traditional scores calculated - Skills: {skills_score}%, Experience: {experience_score}%"
        )

    except Exception as score_error:
        print(f"Error calculating individual scores: {score_error}")

        # It is a Fallback that Use scores from ats_score if available
        skills_score = ats_score.get("skill_match_score", 0)
        experience_score = ats_score.get("experience_score", 0)

        # If still zero, calculate reasonable estimates
        if skills_score == 0 and experience_score == 0:
            overall = ats_score.get("overall_score", 0)
            skills_score = min(
                100, max(0, overall + (len(resume_data.get("skills", [])) * 2))
            )
            experience_score = min(
                100, max(0, overall - 10 + (resume_data.get("total_experience", 0) * 5))
            )

        print(
            f"Using fallback scores - Skills: {skills_score}%, Experience: {experience_score}%"
        )

    return (skills_score, experience_score)
