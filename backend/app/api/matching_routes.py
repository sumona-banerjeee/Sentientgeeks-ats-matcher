"""
✅ FIXED VERSION - matching_routes.py
Complete update with proper session management and validation
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import traceback

from ..models.database import get_db
from ..models.jd_models import JobDescription
from ..models.resume_models import Resume, MatchingResult
from ..services.matching_engine import MatchingEngine

# Importing the Agentic AI Service
try:
    from ..services.agentic_service import EnhancedAgenticATSService as AgenticATSService
    AGENTIC_AVAILABLE = True
    print("✅ Agentic AI Service available")
except ImportError:
    AGENTIC_AVAILABLE = False
    print("⚠️  Agentic AI Service not available - using traditional matching")

router = APIRouter(prefix="/api/matching", tags=["Matching"])

# Checking if the Agentic AI should be used
USE_AGENTIC_AI = os.getenv("USE_AGENTIC_AI", "false").lower() == "true" and AGENTIC_AVAILABLE

# Initializing the services
matching_engine = MatchingEngine()
if USE_AGENTIC_AI:
    try:
        agentic_service = AgenticATSService()
        print("✅ Initialized Agentic AI Service for matching")
    except Exception as e:
        print(f"❌ Failed to initialize Agentic AI: {e}")
        USE_AGENTIC_AI = False
        agentic_service = None
else:
    agentic_service = None
    print("✅ Using traditional matching engine")


@router.post("/start/{session_id}")
async def start_matching(session_id: str, db: Session = Depends(get_db)):
    """
    ✅ FIXED: Start matching with proper session validation
    Prevents cross-session contamination
    """
    
    print(f"\n{'='*70}")
    print(f"🚀 MATCHING REQUEST RECEIVED")
    print(f"   Session ID: {session_id}")
    print(f"   Agentic AI: {'ENABLED' if USE_AGENTIC_AI else 'DISABLED'}")
    print(f"{'='*70}\n")
    
    # ✅ FIX 1: Validate session has resumes BEFORE doing anything
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    if not resumes:
        print(f"❌ No resumes found for session: {session_id}")
        raise HTTPException(
            status_code=400, 
            detail=f"No resumes found for session {session_id}. Please upload resumes first."
        )
    
    print(f"✅ Found {len(resumes)} resumes for session {session_id}")
    
    # ✅ FIX 2: Validate JD exists and is approved for THIS session
    jd = db.query(JobDescription).filter(
        JobDescription.session_id == session_id,
        JobDescription.is_approved == True
    ).first()
    
    if not jd:
        print(f"❌ No approved JD found for session: {session_id}")
        raise HTTPException(
            status_code=400, 
            detail=f"JD not found or not approved for session {session_id}"
        )
    
    # Extract job title safely
    job_title = "Unknown Job"
    if jd.structured_data and isinstance(jd.structured_data, dict):
        job_title = jd.structured_data.get('job_title', jd.structured_data.get('title', 'Unknown Job'))
    
    print(f"✅ Found approved JD: {job_title}")
    
    # ✅ FIX 3: Delete ONLY existing results for THIS specific session
    existing_count = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id
    ).count()
    
    if existing_count > 0:
        print(f"🗑️  Found {existing_count} existing results for session {session_id}")
        print(f"   Deleting old results to ensure fresh matching...")
        
        db.query(MatchingResult).filter(
            MatchingResult.session_id == session_id
        ).delete()
        db.commit()
        
        print(f"✅ Deleted {existing_count} old results")
    else:
        print(f"✅ No existing results found - this is a fresh match")
    
    print(f"\n{'='*70}")
    print(f"STARTING MATCHING PROCESS")
    print(f"   Session: {session_id}")
    print(f"   Job: {job_title}")
    print(f"   Resumes: {len(resumes)}")
    print(f"{'='*70}\n")
    
    # Storing the respective results
    matching_results = []
    
    for i, resume in enumerate(resumes):
        # Add delay to avoid Groq API rate limits
        if i > 0:
            print(f"⏳ Waiting 5 seconds to avoid rate limits...")
            import time
            time.sleep(5)
    
        try:
            print("=" * 70)
            print(f"📄 Processing resume {i+1}/{len(resumes)}: {resume.filename}")
            print(f"   Session: {session_id}")  # ✅ Verify session in logs
            print("=" * 70)
            
            # Ensuring the valid structured data
            jd_data = jd.structured_data if jd.structured_data else {}
            resume_data = resume.structured_data if resume.structured_data else {}
            skills_weightage = jd.skills_weightage if jd.skills_weightage else {}
            
            print(f"📊 JD data keys: {list(jd_data.keys()) if jd_data else 'None'}")
            print(f"📊 Resume data keys: {list(resume_data.keys()) if resume_data else 'None'}")
            
            # Initializing the scores
            overall_score = 0
            skills_score = 0
            experience_score = 0
            detailed_analysis = {}
            
            if USE_AGENTIC_AI and agentic_service:
                try:
                    print("🤖 Using Agentic AI for comprehensive scoring...")
                    
                    # Using agentic AI to match and score
                    agentic_result = await agentic_service.match_and_score(
                        resume_data=resume_data,
                        jd_data=jd_data
                    )
                    
                    print(f"Agentic AI Result: {agentic_result}")
                    
                    # Extracting the scores from agentic result - HANDLE BOTH NAMING CONVENTIONS
                    overall_score = float(
                        agentic_result.get('overallscore') or 
                        agentic_result.get('overall_score') or 0
                    )

                    skills_score = float(
                        agentic_result.get('skillmatchscore') or 
                        agentic_result.get('skill_match_score') or 
                        agentic_result.get('skillMatchScore') or 0
                    )

                    experience_score = float(
                        agentic_result.get('experiencescore') or 
                        agentic_result.get('experience_match_score') or 
                        agentic_result.get('experience_score') or 
                        agentic_result.get('experienceScore') or 0
                    )
                    detailed_analysis = agentic_result.get('detailed_analysis', {})
                    
                    # Adding agentic-specific data to analysis
                    detailed_analysis['scoring_method'] = 'Agentic AI'
                    detailed_analysis['recommendation'] = agentic_result.get('recommendation', 'Unknown')
                    detailed_analysis['matched_skills'] = agentic_result.get('matched_skills', [])
                    detailed_analysis['missing_skills'] = agentic_result.get('missing_skills', [])
                    
                    print(f"✅ Agentic Scores - Overall: {overall_score}%, Skills: {skills_score}%, Experience: {experience_score}%")
                    
                except Exception as agentic_error:
                    print(f"❌ Agentic AI failed: {str(agentic_error)}")
                    print(f"⚠️  Falling back to traditional matching engine...")
                    
                    # Fallback to traditional matching
                    ats_score = matching_engine.calculate_ats_score(
                        jd_data,
                        resume_data,
                        skills_weightage
                    )
                    
                    overall_score = ats_score.get('overall_score', 0)
                    detailed_analysis = ats_score.get('detailed_analysis', {})
                    detailed_analysis['scoring_method'] = 'Traditional (Agentic Fallback)'
                    
                    # Calculating the individual scores using traditional method
                    skills_score, experience_score = _calculate_traditional_scores(
                        jd_data, resume_data, skills_weightage, ats_score
                    )
                    
            else:
                print("✅ Using traditional matching engine...")
                
                # Calculating ATS score using traditional method
                ats_score = matching_engine.calculate_ats_score(
                    jd_data,
                    resume_data,
                    skills_weightage
                )
                
                overall_score = ats_score.get('overall_score', 0)
                detailed_analysis = ats_score.get('detailed_analysis', {})
                detailed_analysis['scoring_method'] = 'Traditional'
                
                # Calculating individual scores
                skills_score, experience_score = _calculate_traditional_scores(
                    jd_data, resume_data, skills_weightage, ats_score
                )
            
            # ✅ FIX 4: Ensure matching result is tied to correct session
            print(f"💾 Saving scores - Overall: {overall_score}%, Skills: {skills_score}%, Experience: {experience_score}%")
            
            matching_result = MatchingResult(
                session_id=session_id,  # ✅ Explicit session binding
                jd_id=jd.id,
                resume_id=resume.id,
                overall_score=round(overall_score, 2),
                skill_match_score=round(skills_score, 2),
                experience_score=round(experience_score, 2),
                detailed_analysis=detailed_analysis,
                rank_position=0  # temporary, updated later
            )
            db.add(matching_result)
            
            # Store in memory for ranking
            matching_results.append({
                "resume_id": resume.id,
                "filename": resume.filename,
                "candidate_name": resume_data.get('name', 'Unknown') if resume_data else 'Unknown',
                "ats_score": {
                    "overall_score": round(overall_score, 2),
                    "skill_match_score": round(skills_score, 2),
                    "experience_score": round(experience_score, 2),
                    "detailed_analysis": detailed_analysis
                }
            })
            
            print(f"✅ Successfully processed: {resume.filename}\n")
        
        except Exception as e:
            print(f"❌ Error processing {resume.filename}: {str(e)}")
            traceback.print_exc()
            
            matching_results.append({
                "resume_id": resume.id,
                "filename": resume.filename,
                "error": str(e)
            })
    
    # RANKING RESUMES BY OVERALL SCORE
    print(f"\n{'='*70}")
    print("📊 RANKING CANDIDATES")
    print(f"{'='*70}\n")
    
    successful_matches = [r for r in matching_results if 'ats_score' in r]
    successful_matches.sort(key=lambda x: x['ats_score']['overall_score'], reverse=True)
    
    # Updating rank positions in DB starting from 1
    for rank, result in enumerate(successful_matches, 1):
        matching_result = db.query(MatchingResult).filter(
            MatchingResult.session_id == session_id,
            MatchingResult.resume_id == result['resume_id']
        ).first()
        if matching_result:
            matching_result.rank_position = rank
            scoring_method = matching_result.detailed_analysis.get('scoring_method', 'Unknown')
            print(f"🏆 Rank #{rank}: {result['filename']} - Score: {result['ats_score']['overall_score']}% [{scoring_method}]")
    
    # Committing all changes
    try:
        db.commit()
        print(f"\n{'='*70}")
        print(f"✅ MATCHING COMPLETED SUCCESSFULLY")
        print(f"   Session: {session_id}")
        print(f"   Successful matches: {len(successful_matches)}")
        print(f"   Failed: {len(matching_results) - len(successful_matches)}")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"❌ Error saving results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error saving matching results")
    
    return {
        "session_id": session_id,
        "total_resumes": len(resumes),
        "successfully_matched": len(successful_matches),
        "ranking": successful_matches,
        "agentic_ai_used": USE_AGENTIC_AI,
        "status": "completed"
    }


@router.get("/results/{session_id}")
async def get_matching_results(session_id: str, db: Session = Depends(get_db)):
    """
    ✅ FIXED: Get results for specific session only with proper validation
    """
    
    print(f"\n{'='*70}")
    print(f"📊 FETCHING MATCHING RESULTS")
    print(f"   Session ID: {session_id}")
    print(f"{'='*70}\n")
    
    # ✅ FIX: Check if resumes exist for this session first
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    if not resumes:
        print(f"❌ No resumes found for session: {session_id}")
        raise HTTPException(
            status_code=400, 
            detail="No resumes found for this session. Please upload resumes first."
        )
    
    print(f"✅ Found {len(resumes)} resumes for session {session_id}")
    
    # ✅ FIX: Get results ONLY for this session, ordered by score
    results = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id
    ).order_by(MatchingResult.overall_score.desc()).all()
    
    print(f"✅ Found {len(results)} matching results")
    
    if not results:
        print(f"⚠️  No matching results found for session: {session_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"No matching results found. Please run the matching process first for the {len(resumes)} uploaded resumes."
        )
    
    # Building detailed results with PROPER SCORING
    detailed_results = []
    for rank, result in enumerate(results, 1):
        resume = db.query(Resume).filter(Resume.id == result.resume_id).first()
        
        if resume:
            resume_data = resume.structured_data if resume.structured_data else {}
            
            # Ensuring scores are properly formatted and not null
            skill_score = result.skill_match_score if result.skill_match_score is not None else 0
            exp_score = result.experience_score if result.experience_score is not None else 0
            
            # Getting scoring method from detailed analysis
            scoring_method = result.detailed_analysis.get('scoring_method', 'Unknown') if result.detailed_analysis else 'Unknown'
            
            detailed_results.append({
                "rank": rank,
                "resume_id": result.resume_id,
                "filename": resume.filename,
                "candidate_name": resume_data.get('name', 'Unknown'),
                "overall_score": round(result.overall_score, 2),
                "skill_match_score": round(skill_score, 2),  
                "experience_score": round(exp_score, 2),     
                "detailed_analysis": result.detailed_analysis or {},
                "skills_found": resume_data.get('skills', []),
                "scoring_method": scoring_method
            })
    
    print(f"✅ Returning {len(detailed_results)} detailed results for session {session_id}")
    print(f"{'='*70}\n")
    
    return {
        "session_id": session_id,
        "total_results": len(detailed_results),
        "results": detailed_results,
        "agentic_ai_used": USE_AGENTIC_AI,
        "status": "success"
    }


@router.get("/detailed/{session_id}/{resume_id}")
async def get_detailed_analysis(session_id: str, resume_id: int, db: Session = Depends(get_db)):
    """
    ✅ FIXED: Get detailed analysis for a specific resume in a session
    """
    
    print(f"\n{'='*70}")
    print(f"🔍 FETCHING DETAILED ANALYSIS")
    print(f"   Session: {session_id}")
    print(f"   Resume ID: {resume_id}")
    print(f"{'='*70}\n")
    
    # ✅ Validate result exists for this session
    result = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id,
        MatchingResult.resume_id == resume_id
    ).first()
    
    if not result:
        print(f"❌ No matching result found for resume {resume_id} in session {session_id}")
        raise HTTPException(status_code=404, detail="Matching result not found")
    
    # ✅ Validate resume and JD exist
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    
    if not resume or not jd:
        print(f"❌ Resume or JD not found")
        raise HTTPException(status_code=404, detail="Resume or JD not found")
    
    print(f"✅ Found matching result and related data")
    
    # Extracting detailed personal information
    resume_data = resume.structured_data or {}
    jd_data = jd.structured_data or {}
    
    # Extracting contact information
    personal_info = {
        "name": resume_data.get('name', 'Unknown'),
        "email": resume_data.get('email', 'Not provided'),
        "phone": resume_data.get('phone', 'Not provided'),
        "linkedin": resume_data.get('linkedin', 'Not provided'),
        "github": resume_data.get('github', 'Not provided'),
        "portfolio": resume_data.get('portfolio', 'Not provided'),
        "location": resume_data.get('location', 'Not provided')
    }
    
    # Extracting professional information
    professional_info = {
        "total_experience": resume_data.get('total_experience', 0),
        "current_role": resume_data.get('current_role', 'Not specified'),
        "skills": resume_data.get('skills', []),
        "education": resume_data.get('education', []),
        "certifications": resume_data.get('certifications', []),
        "experience_timeline": resume_data.get('experience_timeline', [])
    }
    
    # Matching analysis with proper scores
    detailed_analysis = result.detailed_analysis or {}
    skill_score = result.skill_match_score if result.skill_match_score is not None else 0
    exp_score = result.experience_score if result.experience_score is not None else 0
    scoring_method = detailed_analysis.get('scoring_method', 'Unknown')
    
    # Agentic AI specific fields (if available)
    agentic_insights = {}
    if scoring_method == 'Agentic AI':
        agentic_insights = {
            "recommendation": detailed_analysis.get('recommendation', 'Unknown'),
            "matched_skills": detailed_analysis.get('matched_skills', []),
            "missing_skills": detailed_analysis.get('missing_skills', []),
            "strengths": detailed_analysis.get('strengths', []),
            "weaknesses": detailed_analysis.get('weaknesses', []),
            "key_highlights": detailed_analysis.get('key_highlights', [])
        }
    
    print(f"✅ Returning detailed analysis")
    print(f"   Rank: #{result.rank_position}")
    print(f"   Overall Score: {result.overall_score}%")
    print(f"   Scoring Method: {scoring_method}")
    print(f"{'='*70}\n")
    
    return {
        "resume_info": {
            "id": resume.id,
            "filename": resume.filename,
            "personal_info": personal_info,
            "professional_info": professional_info,
            "structured_data": resume_data  # ✅ Include full structured data
        },
        "jd_info": {
            "job_title": jd_data.get('job_title', 'Unknown'),
            "company": jd_data.get('company', 'Unknown'),
            "required_skills": jd_data.get('primary_skills', []) + jd_data.get('secondary_skills', []),
            "experience_required": jd_data.get('experience_required', 'Not specified')
        },
        "matching_analysis": {
            "rank": result.rank_position,
            "rank_position": result.rank_position,
            "overall_score": round(result.overall_score, 2),
            "skill_match_score": round(skill_score, 2),     
            "experience_score": round(exp_score, 2),
            "detailed_analysis": detailed_analysis,
            "scoring_method": scoring_method,
            "agentic_insights": agentic_insights if agentic_insights else None
        }
    }


# ✅ HELPER FUNCTION FOR TRADITIONAL SCORING
def _calculate_traditional_scores(
    jd_data: dict, 
    resume_data: dict, 
    skills_weightage: dict, 
    ats_score: dict
) -> tuple[float, float]:
    """
    Use LLM-based ATS scores directly.
    Traditional rule-based scoring has been fully deprecated.
    """

    # ✅ DIRECTLY RETURN LLM SCORES
    skills_score = ats_score.get('skill_match_score', 0)
    experience_score = ats_score.get('experience_score', 0)

    # Safety clamp (0–100)
    skills_score = max(0, min(100, skills_score))
    experience_score = max(0, min(100, experience_score))

    print(
        f"   Using LLM scores - "
        f"Skills: {skills_score}%, "
        f"Experience: {experience_score}%"
    )

    return skills_score, experience_score


# ✅ OPTIONAL: Debug endpoint to check session state
@router.get("/debug/session/{session_id}")
async def debug_session_state(session_id: str, db: Session = Depends(get_db)):
    """
    Debug endpoint to check session state
    Only enable in development!
    """
    
    jd_count = db.query(JobDescription).filter(
        JobDescription.session_id == session_id
    ).count()
    
    resume_count = db.query(Resume).filter(
        Resume.session_id == session_id
    ).count()
    
    result_count = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id
    ).count()
    
    return {
        "session_id": session_id,
        "jd_count": jd_count,
        "resume_count": resume_count,
        "matching_result_count": result_count,
        "has_jd": jd_count > 0,
        "has_resumes": resume_count > 0,
        "has_results": result_count > 0,
        "status": "debug_info"
    }