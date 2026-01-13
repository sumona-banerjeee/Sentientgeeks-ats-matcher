"""
Enhanced LLM-Powered ATS Matching Engine
FAIR VERSION: Semantic matching, no unfair zeros, intelligent scoring
"""

import spacy
from typing import Dict, List, Any, Tuple
import re
from datetime import datetime
import traceback

class MatchingEngine:
    def __init__(self):
        """Initialize intelligent matching engine"""
        try:
            self.nlp = spacy.load("en_core_web_md")
            print("✅ spaCy model loaded")
        except OSError:
            print("⚠️ spaCy model not found")
            self.nlp = None
        
        # Initialize llamacpp service
        try:
            from backend.app.services.llamacpp_service import get_llamacpp_service
            self.llamacpp = get_llamacpp_service()
            self.use_llm = True
            print("✅ LLM-based intelligent matching enabled (FAIR MODE)")
        except Exception as e:
            print(f"⚠️ LLM not available: {e}")
            self.llamacpp = None
            self.use_llm = False
    
    def calculate_ats_score(
        self, 
        jd_data: dict, 
        resume_data: dict, 
        skills_weightage: dict, 
        manual_priorities: List[Dict] = None
    ) -> dict:
        """
        LLM-POWERED INTELLIGENT ATS SCORING WITH FAIR MATCHING
        
        KEY FEATURES:
        1. Semantic skill matching (Python matches "Python (Pandas, NumPy)")
        2. Role-based skill inference (Python Developer knows Python)
        3. Fair scoring for career changers
        4. No unfair zeros unless truly irrelevant
        5. Partial credit for similar skills
        """
        
        print(f"\n{'='*70}")
        print(f"🧠 FAIR LLM-BASED ATS SCORING")
        print(f"{'='*70}\n")
        
        if not jd_data or not resume_data:
            return self._get_default_score("Missing data")
        
        try:
            # Extract data
            jd_title = jd_data.get('job_title', 'Unknown Position')
            jd_primary_skills = jd_data.get('primary_skills', [])
            jd_secondary_skills = jd_data.get('secondary_skills', [])
            jd_experience_required = jd_data.get('experience_required', '0-2 years')
            
            resume_skills = self._extract_resume_skills(resume_data)
            experience_timeline = resume_data.get('experience_timeline', [])
            candidate_name = resume_data.get('name', 'Unknown')
            total_experience_years = resume_data.get('total_experience', 0)
            
            print(f"📋 JD: {jd_title}")
            print(f"   Primary Skills: {len(jd_primary_skills)} required")
            print(f"   Experience: {jd_experience_required}")
            
            print(f"\n👤 Candidate: {candidate_name}")
            print(f"   Skills: {len(resume_skills)}")
            print(f"   Experience: {total_experience_years} years")
            
            # STEP 1: SMART Skill Matching (50% weight)
            if self.use_llm and self.llamacpp:
                skill_analysis = self.llamacpp.enhanced_skill_matching(
                    resume_data=resume_data,
                    resume_skills=resume_skills,
                    jd_primary_skills=jd_primary_skills,
                    jd_secondary_skills=jd_secondary_skills,
                    skills_weightage=skills_weightage,
                    experience_timeline=experience_timeline
                )
            else:
                skill_analysis = self._fallback_skill_matching(
                    resume_skills, jd_primary_skills, jd_secondary_skills, skills_weightage
                )
            
            skill_score = skill_analysis.get('skill_match_score', 0)
            
            print(f"\n✅ SKILL SCORE: {skill_score:.1f}/100")
            print(f"   Matched: {skill_analysis.get('matched_primary_count', 0)}/{len(jd_primary_skills)}")
            print(f"   Semantic Matches: {skill_analysis.get('semantic_matches_applied', 0)}")
            print(f"   Role Inferences: {skill_analysis.get('role_inferences_applied', 0)}")
            
            # STEP 2: FAIR Experience Matching (50% weight)
            if self.use_llm and self.llamacpp:
                experience_analysis = self.llamacpp.enhanced_experience_matching(
                    experience_timeline=experience_timeline,
                    jd_role=jd_title,
                    jd_experience_required=jd_experience_required,
                    jd_primary_skills=jd_primary_skills,
                    skills_weightage=skills_weightage,
                    total_experience_years=total_experience_years,
                    skill_match_score=skill_score
                )
            else:
                experience_analysis = self._fallback_experience_matching(
                    experience_timeline, jd_title, jd_experience_required, total_experience_years
                )
            
            experience_score = experience_analysis.get('experience_match_score', 0)
            
            print(f"\n✅ EXPERIENCE SCORE: {experience_score:.1f}/100")
            print(f"   Role Relevance: {experience_analysis.get('role_relevance_percentage', 0)}%")
            print(f"   Matching Roles: {len(experience_analysis.get('matching_roles', []))}")
            
            # STEP 3: Final Score Calculation
            if self.use_llm and self.llamacpp:
                final_analysis = self.llamacpp.calculate_final_ats_score_v2(
                    skill_analysis=skill_analysis,
                    experience_analysis=experience_analysis,
                    candidate_name=candidate_name,
                    jd_title=jd_title,
                    jd_experience_required=jd_experience_required,
                    total_experience_years=total_experience_years
                )
            else:
                overall_score = (skill_score + experience_score) / 2
                final_analysis = {
                    "overall_score": overall_score,
                    "skill_component": skill_score,
                    "experience_component": experience_score,
                    "recommendation": self._get_recommendation(overall_score),
                    "hiring_decision": self._get_hiring_decision(overall_score)
                }
            
            overall_score = final_analysis.get('overall_score', 0)
            
            print(f"\n📊 FINAL SCORE: {overall_score:.1f}/100")
            print(f"   Skills (50%): {skill_score:.1f}")
            print(f"   Experience (50%): {experience_score:.1f}")
            print(f"   Recommendation: {final_analysis.get('recommendation', 'N/A')}")
            print(f"{'='*70}\n")
            
            # Build detailed analysis
            detailed_analysis = {
                "scoring_method": "Fair LLM-Powered Intelligent Matching",
                "formula": "50% Skills (Semantic + Fuzzy) + 50% Experience (Fair Role Matching)",
                "skill_analysis": skill_analysis,
                "experience_analysis": experience_analysis,
                "final_assessment": final_analysis,
                "candidate_info": {
                    "name": candidate_name,
                    "total_skills": len(resume_skills),
                    "total_experience_years": total_experience_years
                }
            }
            
            return {
                "overall_score": round(min(100, max(0, overall_score)), 2),
                "skill_match_score": round(skill_score, 2),
                "experience_score": round(experience_score, 2),
                "qualification_score": 75.0,
                "detailed_analysis": detailed_analysis
            }
            
        except Exception as e:
            print(f"❌ Error in ATS scoring: {str(e)}")
            traceback.print_exc()
            return self._get_default_score(str(e))
    
    def _extract_resume_skills(self, resume_data: Dict) -> List[Dict]:
        """Extract all skills with context and source"""
        skills_with_context = []
        
        # Skills from skills section
        if 'skills' in resume_data and isinstance(resume_data['skills'], list):
            for skill in resume_data['skills']:
                if skill and skill.strip():
                    skills_with_context.append({
                        "skill": skill.strip().lower(),
                        "source": "skills_section",
                        "context": "Listed in skills section"
                    })
        
        # Skills from experience
        experience_timeline = resume_data.get('experience_timeline', [])
        for exp in experience_timeline:
            techs = exp.get('technologies_used', [])
            role = exp.get('role', '')
            company = exp.get('company', '')
            duration = exp.get('duration', '')
            
            if isinstance(techs, list):
                for tech in techs:
                    if tech and tech.strip():
                        skills_with_context.append({
                            "skill": tech.strip().lower(),
                            "source": "experience",
                            "context": f"{role} at {company} ({duration})"
                        })
        
        return skills_with_context
    
    def _fallback_skill_matching(
        self, 
        resume_skills: list, 
        primary_skills: list, 
        secondary_skills: list,
        skills_weightage: dict
    ) -> dict:
        """Improved fallback with fuzzy matching"""
        print("⚠️ Using improved fallback skill matching")
        
        # Extract skill names
        resume_skill_names = set()
        for s in resume_skills:
            if isinstance(s, dict):
                resume_skill_names.add(s['skill'].lower())
            else:
                resume_skill_names.add(str(s).lower())
        
        matched_primary = []
        missing_primary = []
        
        # Fuzzy matching
        for jd_skill in primary_skills:
            jd_skill_clean = jd_skill.lower().strip()
            
            # Extract core skill (remove parentheses content)
            core_skill = re.sub(r'\([^)]*\)', '', jd_skill_clean).strip()
            
            # Check for match
            matched = False
            for resume_skill in resume_skill_names:
                if (core_skill in resume_skill or 
                    resume_skill in core_skill or
                    self._skills_similar(core_skill, resume_skill)):
                    matched_primary.append(jd_skill)
                    matched = True
                    break
            
            if not matched:
                missing_primary.append(jd_skill)
        
        # Calculate score
        match_rate = len(matched_primary) / len(primary_skills) if primary_skills else 0
        base_score = match_rate * 100
        
        # Apply minimum floor
        if len(matched_primary) > 0:
            base_score = max(base_score, 20)
        elif len(resume_skills) > 5:
            base_score = 15  # Has skills, just not exact matches
        
        return {
            "skill_match_score": min(100, base_score),
            "matched_primary_count": len(matched_primary),
            "total_primary_count": len(primary_skills),
            "matched_primary_skills": matched_primary,
            "missing_primary_skills": missing_primary,
            "reasoning": f"Fuzzy matching: {len(matched_primary)}/{len(primary_skills)} matched"
        }
    
    def _skills_similar(self, skill1: str, skill2: str) -> bool:
        """Check if skills are similar"""
        # Remove common suffixes/prefixes
        skill1 = skill1.replace('js', 'javascript').replace('.js', '')
        skill2 = skill2.replace('js', 'javascript').replace('.js', '')
        
        # Common equivalences
        equivalences = [
            {'python', 'python3', 'python programming'},
            {'javascript', 'js', 'ecmascript'},
            {'sql', 'mysql', 'postgresql', 'sql server'},
            {'react', 'reactjs', 'react.js'},
            {'node', 'nodejs', 'node.js'},
        ]
        
        for equiv_set in equivalences:
            if skill1 in equiv_set and skill2 in equiv_set:
                return True
        
        # Check if one contains the other
        if len(skill1) > 3 and len(skill2) > 3:
            if skill1 in skill2 or skill2 in skill1:
                return True
        
        return False
    
    def _fallback_experience_matching(
        self,
        experience_timeline: list,
        jd_role: str,
        jd_experience_required: str,
        total_experience_years: float
    ) -> dict:
        """Improved fallback experience matching"""
        print("⚠️ Using improved fallback experience matching")
        
        # Calculate total years
        total_years = total_experience_years if total_experience_years > 0 else \
                     sum(self._extract_years_from_duration(exp.get('duration', '')) 
                         for exp in experience_timeline)
        
        # Role matching with fuzzy logic
        jd_keywords = set(jd_role.lower().split())
        best_relevance = 0
        
        for exp in experience_timeline:
            exp_role = exp.get('role', '').lower()
            exp_keywords = set(exp_role.split())
            
            # Calculate similarity
            if exp_role == jd_role.lower():
                relevance = 95
            elif 'intern' in exp_role and any(k in exp_role for k in jd_keywords):
                relevance = 75
            else:
                # Count matching keywords
                matches = len(jd_keywords & exp_keywords)
                relevance = min(80, matches * 25)
            
            best_relevance = max(best_relevance, relevance)
        
        # Calculate base score
        base_score = (best_relevance / 100) * 70 + 20  # Minimum 20%
        
        # Apply experience level adjustment
        exp_range = self._parse_experience_range(jd_experience_required)
        if exp_range['min'] <= total_years <= exp_range['max']:
            multiplier = 1.2
        elif total_years < exp_range['min']:
            multiplier = 0.8
        else:
            multiplier = 0.9
        
        final_score = min(100, base_score * multiplier)
        
        return {
            "experience_match_score": final_score,
            "role_relevance_percentage": best_relevance,
            "relevant_experience_years": total_years,
            "has_matching_role_experience": best_relevance > 50,
            "reasoning": f"Fallback: {best_relevance}% role relevance, {total_years} years"
        }
    
    def _parse_experience_range(self, exp_str: str) -> dict:
        """Parse experience range"""
        exp_str = exp_str.lower().strip()
        
        if '+' in exp_str:
            match = re.search(r'(\d+)\+', exp_str)
            if match:
                return {"min": int(match.group(1)), "max": 100}
        
        match = re.search(r'(\d+)\s*-\s*(\d+)', exp_str)
        if match:
            return {"min": int(match.group(1)), "max": int(match.group(2))}
        
        match = re.search(r'(\d+)', exp_str)
        if match:
            years = int(match.group(1))
            return {"min": years, "max": years + 2}
        
        return {"min": 0, "max": 2}
    
    def _extract_years_from_duration(self, duration_str: str) -> float:
        """Extract years from duration"""
        if not duration_str:
            return 0.5
        
        duration_str = duration_str.lower().strip()
        
        # Handle "present/current"
        if 'present' in duration_str or 'current' in duration_str:
            year_match = re.search(r'(\d{4})', duration_str)
            if year_match:
                start_year = int(year_match.group(1))
                return max(0.1, datetime.now().year - start_year)
        
        # Handle year ranges
        year_matches = re.findall(r'(\d{4})', duration_str)
        if len(year_matches) >= 2:
            return max(0.1, int(year_matches[-1]) - int(year_matches[0]))
        
        # Handle explicit years
        years_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', duration_str)
        if years_match:
            return float(years_match.group(1))
        
        # Handle months
        months_match = re.search(r'(\d+)\s*months?', duration_str)
        if months_match:
            return max(0.1, int(months_match.group(1)) / 12)
        
        return 1.0
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on score"""
        if score >= 75:
            return "strong_fit"
        elif score >= 55:
            return "good_fit"
        elif score >= 35:
            return "moderate_fit"
        elif score >= 20:
            return "weak_fit"
        else:
            return "poor_fit"
    
    def _get_hiring_decision(self, score: float) -> str:
        """Get hiring decision based on score"""
        if score >= 75:
            return "highly_recommended"
        elif score >= 55:
            return "recommended"
        elif score >= 35:
            return "consider"
        elif score >= 20:
            return "interview_to_decide"
        else:
            return "not_recommended"
    
    def _get_default_score(self, error_msg: str) -> dict:
        """Default score with minimum fairness"""
        return {
            "overall_score": 20,  # Minimum 20% instead of 0
            "skill_match_score": 15,
            "experience_score": 25,
            "detailed_analysis": {
                "error": error_msg,
                "note": "Using minimum default scores"
            }
        }