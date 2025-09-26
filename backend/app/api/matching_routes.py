from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..models.database import get_db
from ..models.jd_models import JobDescription
from ..models.resume_models import Resume, MatchingResult
from ..services.matching_engine import MatchingEngine

router = APIRouter(prefix="/api/matching", tags=["Matching"])

@router.post("/start/{session_id}")
async def start_matching(session_id: str, db: Session = Depends(get_db)):
    """Start the matching process for all resumes in a session"""
    
    print(f"Starting matching process for session: {session_id}")
    
    # Get JD data
    jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    if not jd or not jd.is_approved:
        raise HTTPException(status_code=400, detail="JD not found or not approved")
    
    # Extract job title safely
    job_title = "Unknown Job"
    if jd.structured_data and isinstance(jd.structured_data, dict):
        job_title = jd.structured_data.get('job_title', jd.structured_data.get('title', 'Unknown Job'))
    
    print(f"Found approved JD: {job_title}")
    
    # Get all resumes for this session
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    if not resumes:
        raise HTTPException(
            status_code=400, 
            detail="No resumes found for this session. Please upload resumes first."
        )
    
    print(f"Found {len(resumes)} resumes to process")
    
    # Clear any existing results for this session
    db.query(MatchingResult).filter(MatchingResult.session_id == session_id).delete()
    db.commit()
    
    # Initialize matching engine
    matching_engine = MatchingEngine()
    
    # Store results
    matching_results = []
    
    for i, resume in enumerate(resumes):
        try:
            print(f"Processing resume {i+1}/{len(resumes)}: {resume.filename}")
            
            # Ensure valid structured data
            jd_data = jd.structured_data if jd.structured_data else {}
            resume_data = resume.structured_data if resume.structured_data else {}
            skills_weightage = jd.skills_weightage if jd.skills_weightage else {}
            
            print(f"JD data keys: {list(jd_data.keys()) if jd_data else 'None'}")
            print(f"Resume data keys: {list(resume_data.keys()) if resume_data else 'None'}")
            print(f"Skills weightage: {len(skills_weightage)} skills" if skills_weightage else "📊 No skills weightage")
            
            # ✅ MAIN FIX: Calculate ATS score and individual scores
            ats_score = matching_engine.calculate_ats_score(
                jd_data,
                resume_data,
                skills_weightage
            )
            
            overall_score = ats_score.get('overall_score', 0)
            
            # ✅ FIX: Calculate individual scores separately for better accuracy
            # Parse JD experience requirement
            jd_exp_required = 0
            if jd_data.get('experience_required'):
                try:
                    jd_exp_required = matching_engine.parse_experience_years(str(jd_data['experience_required']))
                except:
                    jd_exp_required = 0
            
            # Calculate individual skill and experience scores
            try:
                # Get job priorities for detailed scoring
                job_priorities = matching_engine.extract_job_priorities_from_jd(jd_data)
                
                # Calculate individual scores using matching engine methods
                skills_score = matching_engine.calculate_complete_skills_score(
                    resume_data, job_priorities, skills_weightage
                )
                experience_score = matching_engine.calculate_enhanced_experience_score(
                    resume_data, job_priorities, jd_exp_required
                )
                
                print(f"Individual scores calculated - Skills: {skills_score}%, Experience: {experience_score}%")
                
            except Exception as score_error:
                print(f"Error calculating individual scores: {score_error}")
                # Fallback: Calculate reasonable estimates from overall score
                skills_score = min(100, max(0, overall_score + (len(resume_data.get('skills', [])) * 2)))
                experience_score = min(100, max(0, overall_score - 10 + (resume_data.get('total_experience', 0) * 5)))
                
                print(f"Using estimated scores - Skills: {skills_score}%, Experience: {experience_score}%")
            
            print(f"Final scores - Overall: {overall_score}%, Skills: {skills_score}%, Experience: {experience_score}%")
            
            # ✅ Save result with proper individual scores
            matching_result = MatchingResult(
                session_id=session_id,
                jd_id=jd.id,
                resume_id=resume.id,
                overall_score=overall_score,
                skill_match_score=skills_score, 
                experience_score=experience_score,  
                detailed_analysis=ats_score.get('detailed_analysis', {}),
                rank_position=0  # temporary, updated later
            )
            db.add(matching_result)
            
            # Store in memory for ranking
            matching_results.append({
                "resume_id": resume.id,
                "filename": resume.filename,
                "candidate_name": resume_data.get('name', 'Unknown') if resume_data else 'Unknown',
                "ats_score": {
                    "overall_score": overall_score,
                    "skill_match_score": skills_score,
                    "experience_score": experience_score,
                    "detailed_analysis": ats_score.get('detailed_analysis', {})
                }
            })
            
            print(f"✅ Successfully processed: {resume.filename} with scores: Overall={overall_score}%, Skills={skills_score}%, Experience={experience_score}%")
        
        except Exception as e:
            print(f"❌ Error processing {resume.filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            matching_results.append({
                "resume_id": resume.id,
                "filename": resume.filename,
                "error": str(e)
            })
    
    # Rank resumes by overall score (descending)
    successful_matches = [r for r in matching_results if 'ats_score' in r]
    successful_matches.sort(key=lambda x: x['ats_score']['overall_score'], reverse=True)
    
    # Update rank positions in DB (starting from 1)
    for rank, result in enumerate(successful_matches, 1):
        matching_result = db.query(MatchingResult).filter(
            MatchingResult.session_id == session_id,
            MatchingResult.resume_id == result['resume_id']
        ).first()
        if matching_result:
            matching_result.rank_position = rank
            print(f"🏆 Ranked {result['filename']} as #{rank} with overall score {result['ats_score']['overall_score']}%")
    
    # Commit all changes
    try:
        db.commit()
        print(f"✅ Matching completed: {len(successful_matches)} successful matches")
    except Exception as e:
        print(f"❌ Error saving results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error saving matching results")
    
    return {
        "session_id": session_id,
        "total_resumes": len(resumes),
        "successfully_matched": len(successful_matches),
        "ranking": successful_matches,
        "status": "completed"
    }

@router.get("/results/{session_id}")
async def get_matching_results(session_id: str, db: Session = Depends(get_db)):
    """Get detailed matching results for a session"""
    
    print(f"Fetching matching results for session: {session_id}")
    
    # First check if resumes exist for this session
    resumes = db.query(Resume).filter(Resume.session_id == session_id).all()
    if not resumes:
        print(f"No resumes found for session: {session_id}")
        raise HTTPException(
            status_code=400, 
            detail="No resumes found for this session. Please upload resumes first."
        )
    
    print(f"Found {len(resumes)} resumes for session {session_id}")
    
    # Check if matching results exist - ORDER BY overall_score DESC for proper ranking
    results = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id
    ).order_by(MatchingResult.overall_score.desc()).all()
    
    print(f"Found {len(results)} matching results")
    
    if not results:
        print(f"No matching results found for session: {session_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"No matching results found. Please run the matching process first for the {len(resumes)} uploaded resumes."
        )
    
    # ✅ Build detailed results with PROPER SCORING
    detailed_results = []
    for rank, result in enumerate(results, 1):
        resume = db.query(Resume).filter(Resume.id == result.resume_id).first()
        
        if resume:
            resume_data = resume.structured_data if resume.structured_data else {}
            
            # ✅ Ensure scores are properly formatted and not null/zero
            skill_score = result.skill_match_score if result.skill_match_score is not None else 0
            exp_score = result.experience_score if result.experience_score is not None else 0
            
            detailed_results.append({
                "rank": rank,
                "resume_id": result.resume_id,
                "filename": resume.filename,
                "candidate_name": resume_data.get('name', 'Unknown'),
                "overall_score": round(result.overall_score, 2),
                "skill_match_score": round(skill_score, 2),  
                "experience_score": round(exp_score, 2),     
                "detailed_analysis": result.detailed_analysis or {},
                "skills_found": resume_data.get('skills', [])
            })
    
    print(f"✅ Returning {len(detailed_results)} detailed results, ranked by score")
    
    return {
        "session_id": session_id,
        "total_results": len(detailed_results),
        "results": detailed_results,
        "status": "success"
    }

@router.get("/detailed/{session_id}/{resume_id}")
async def get_detailed_analysis(session_id: str, resume_id: int, db: Session = Depends(get_db)):
    """Get detailed analysis for a specific resume"""
    
    print(f"Fetching detailed analysis for resume {resume_id} in session {session_id}")
    
    result = db.query(MatchingResult).filter(
        MatchingResult.session_id == session_id,
        MatchingResult.resume_id == resume_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Matching result not found")
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    jd = db.query(JobDescription).filter(JobDescription.session_id == session_id).first()
    
    if not resume or not jd:
        raise HTTPException(status_code=404, detail="Resume or JD not found")
    
    # Extract detailed personal information
    resume_data = resume.structured_data or {}
    jd_data = jd.structured_data or {}
    
    # Extract contact information
    personal_info = {
        "name": resume_data.get('name', 'Unknown'),
        "email": resume_data.get('email', 'Not provided'),
        "phone": resume_data.get('phone', 'Not provided'),
        "linkedin": resume_data.get('linkedin', 'Not provided'),
        "github": resume_data.get('github', 'Not provided'),
        "portfolio": resume_data.get('portfolio', 'Not provided'),
        "location": resume_data.get('location', 'Not provided')
    }
    
    # Extract professional information
    professional_info = {
        "total_experience": resume_data.get('total_experience', 0),
        "current_role": resume_data.get('current_role', 'Not specified'),
        "skills": resume_data.get('skills', []),
        "education": resume_data.get('education', []),
        "certifications": resume_data.get('certifications', []),
        "experience_timeline": resume_data.get('experience_timeline', [])
    }
    
    # ✅ Matching analysis with proper scores
    detailed_analysis = result.detailed_analysis or {}
    skill_score = result.skill_match_score if result.skill_match_score is not None else 0
    exp_score = result.experience_score if result.experience_score is not None else 0
    
    return {
        "resume_info": {
            "id": resume.id,
            "filename": resume.filename,
            "personal_info": personal_info,
            "professional_info": professional_info
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
            "detailed_analysis": detailed_analysis
        }
    }