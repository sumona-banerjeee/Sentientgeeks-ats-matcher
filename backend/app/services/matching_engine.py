import spacy
from typing import Dict, List, Any, Tuple
import re
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
import traceback

class MatchingEngine:
    def __init__(self):
        """Initialize the enhanced matching engine with strict experience relevance"""
        try:
            try:
                self.nlp = spacy.load("en_core_web_md")
                print("spaCy medium model loaded successfully")
            except OSError:
                self.nlp = spacy.load("en_core_web_sm")
                print("spaCy small model loaded as fallback")
        except OSError:
            print("spaCy model not found, using basic matching")
            self.nlp = None
    
    def calculate_ats_score(self, jd_data: dict, resume_data: dict, skills_weightage: dict, manual_priorities: List[Dict] = None) -> dict:
        """
        Calculate ATS score with STRICT experience relevance matching
        
        Key Changes:
        - Candidates without relevant job role experience get 0 overall score
        - Only experience in matching roles contributes to scoring
        - Universal system works for any job description
        """
        
        print(f"\n{'='*70}")
        print(f"STARTING STRICT EXPERIENCE-BASED ATS SCORING")
        print(f"{'='*70}\n")
        
        if not jd_data or not resume_data:
            return self._get_default_score("Missing JD or resume data")
        
        try:
            # STEP 1: Extract JD Requirements
            jd_experience_required = self._extract_experience_requirement(jd_data)
            job_priorities = self._extract_job_priorities(jd_data, manual_priorities)
            
            print(f"📋 JD Analysis:")
            print(f"   Required Experience: {jd_experience_required} years")
            print(f"   Job Priorities: {[(p['role'], p['priority']) for p in job_priorities]}")
            
            # STEP 2: Extract and Enhance Resume Data
            resume_skills = self._extract_resume_skills(resume_data)
            enhanced_experience = self._enhance_experience_data(resume_data, job_priorities)
            
            enhanced_resume_data = resume_data.copy()
            enhanced_resume_data['skills'] = resume_skills
            enhanced_resume_data['experience_timeline'] = enhanced_experience
            
            print(f"\n👤 Resume Analysis:")
            print(f"   Total Experience: {resume_data.get('total_experience', 0)} years")
            print(f"   Skills: {len(resume_skills)} identified")
            print(f"   Experience Timeline: {len(enhanced_experience)} jobs")
            
            # STEP 3: Calculate Relevant Experience (CRITICAL)
            relevant_experience_years, relevance_details = self._calculate_relevant_experience(
                enhanced_experience, job_priorities)
            
            print(f"\n🎯 RELEVANT EXPERIENCE CHECK:")
            print(f"   Total Relevant Experience: {relevant_experience_years:.1f} years")
            print(f"   Matching Jobs: {relevance_details['matching_jobs_count']}")
            
            # STEP 4: STRICT FILTERING - No relevant experience = 0 score
            if relevant_experience_years == 0 or relevance_details['matching_jobs_count'] == 0:
                print(f"\n❌ REJECTED: No relevant job role experience found")
                print(f"   Candidate has no experience matching: {[p['role'] for p in job_priorities]}")
                
                return {
                    "overall_score": 0.0,
                    "skill_match_score": 0.0,
                    "experience_score": 0.0,
                    "qualification_score": 0.0,
                    "detailed_analysis": {
                        "rejection_reason": "No relevant job role experience",
                        "required_roles": [p['role'] for p in job_priorities],
                        "candidate_experience": [
                            {
                                "role": exp.get('role', 'Unknown'),
                                "company": exp.get('company', 'Unknown'),
                                "duration": exp.get('duration', 'Unknown')
                            }
                            for exp in enhanced_experience
                        ],
                        "relevant_experience_years": 0.0,
                        "matching_jobs_count": 0
                    }
                }
            
            # STEP 5: Calculate Scores (only for candidates with relevant experience)
            print(f"\n✅ QUALIFIED: Candidate has relevant experience")
            
            # Skills Score (0-100)
            skills_score = self._calculate_complete_skills_score(
                enhanced_resume_data, job_priorities, skills_weightage
            )
            
            # Experience Score (0-100) - considers ONLY relevant experience
            experience_score = self._calculate_enhanced_experience_score_v2(
                enhanced_resume_data, job_priorities, jd_experience_required,
                relevant_experience_years, relevance_details
            )
            
            # STEP 6: Final Score Calculation
            total_experience = resume_data.get('total_experience', 0)
            is_fresh_graduate = (total_experience == 0 or not enhanced_experience)
            
            if is_fresh_graduate:
                if jd_experience_required > 0:
                    penalty = min(30, jd_experience_required * 10)
                    final_score = max(0, skills_score - penalty)
                    score_method = f"Skills-Based with {penalty}% experience penalty"
                else:
                    final_score = skills_score
                    score_method = "Skills-Based (No experience required)"
            else:
                # Average of skills and experience (both weighted equally)
                final_score = (skills_score + experience_score) / 2
                score_method = "Skills + Relevant Experience Average"
            
            print(f"\n📊 FINAL SCORES:")
            print(f"   Skills Score: {skills_score:.1f}/100")
            print(f"   Experience Score: {experience_score:.1f}/100")
            print(f"   Overall Score: {final_score:.1f}/100")
            print(f"   Method: {score_method}")
            
            # STEP 7: Detailed Analysis
            detailed_analysis = {
                "job_priorities": job_priorities,
                "jd_experience_required": jd_experience_required,
                "candidate_total_experience": total_experience,
                "candidate_relevant_experience": relevant_experience_years,
                "scoring_method": score_method,
                "is_fresh_graduate": is_fresh_graduate,
                "relevance_check": {
                    "has_relevant_experience": True,
                    "relevant_years": relevant_experience_years,
                    "matching_jobs": relevance_details['matching_jobs'],
                    "matching_jobs_count": relevance_details['matching_jobs_count']
                },
                "skills_analysis": self._get_complete_skills_analysis(
                    enhanced_resume_data, job_priorities, skills_weightage
                ),
                "experience_analysis": self._get_enhanced_experience_analysis(
                    enhanced_resume_data, job_priorities, jd_experience_required
                ),
                "scoring_breakdown": {
                    "skills_score": round(skills_score, 2),
                    "experience_score": round(experience_score, 2),
                    "final_score": round(final_score, 2),
                    "scoring_method": score_method,
                    "meets_experience_requirement": relevant_experience_years >= jd_experience_required
                }
            }
            
            print(f"{'='*70}\n")
            
            return {
                "overall_score": round(min(100, max(0, final_score)), 2),
                "skill_match_score": round(skills_score, 2),
                "experience_score": round(experience_score, 2),
                "qualification_score": 75.0,
                "detailed_analysis": detailed_analysis
            }
            
        except Exception as e:
            print(f"❌ Error in matching calculation: {str(e)}")
            traceback.print_exc()
            return self._get_default_score(str(e))
    
    def _calculate_relevant_experience(
        self, 
        experience_timeline: List[Dict], 
        job_priorities: List[Dict]
    ) -> Tuple[float, Dict]:
        """
        Calculate ONLY relevant experience that matches JD requirements
        
        Returns:
            - Total relevant experience in years
            - Details about matching jobs
        """
        
        if not experience_timeline:
            return (0.0, {
                "matching_jobs": [],
                "matching_jobs_count": 0,
                "non_matching_jobs": []
            })
        
        # Collect all required role keywords from priorities
        required_role_keywords = set()
        priority_skills = set()
        
        for priority in job_priorities:
            role_name = priority['role'].lower()
            key_skills = [skill.lower() for skill in priority['key_skills']]
            
            # Extract role keywords (remove common suffixes)
            role_keywords = role_name.replace(' developer', '').replace(' engineer', '').split()
            required_role_keywords.update(role_keywords)
            priority_skills.update(key_skills)
        
        print(f"\n🔍 Required Role Keywords: {required_role_keywords}")
        print(f"🔍 Priority Skills: {list(priority_skills)[:10]}")
        
        # Analyze each job experience
        relevant_years = 0.0
        matching_jobs = []
        non_matching_jobs = []
        
        for exp in experience_timeline:
            exp_role = exp.get('role', '').lower()
            exp_techs = [tech.lower() for tech in exp.get('technologies_used', [])]
            exp_duration = exp.get('duration', '')
            exp_company = exp.get('company', '')
            
            # Calculate years for this experience
            years = self._extract_years_from_duration(exp_duration)
            
            # Check if this experience is relevant
            is_relevant = False
            relevance_score = 0.0
            matching_reasons = []
            
            # Check 1: Role title matching
            role_match_count = 0
            for keyword in required_role_keywords:
                if keyword in exp_role and keyword not in ['developer', 'engineer', 'software']:
                    role_match_count += 1
                    matching_reasons.append(f"Role contains '{keyword}'")
            
            if role_match_count > 0:
                relevance_score += 0.5
                is_relevant = True
            
            # Check 2: Technology/Skills matching
            tech_match_count = 0
            matched_techs = []
            for skill in priority_skills:
                if any(skill in tech for tech in exp_techs):
                    tech_match_count += 1
                    matched_techs.append(skill)
            
            if tech_match_count >= 2:  # At least 2 matching technologies
                relevance_score += 0.5
                is_relevant = True
                matching_reasons.append(f"{tech_match_count} matching technologies")
            
            # Determine if job is relevant
            if is_relevant and relevance_score >= 0.5:
                relevant_years += years
                matching_jobs.append({
                    "role": exp.get('role', 'Unknown'),
                    "company": exp_company,
                    "duration": exp_duration,
                    "years": years,
                    "relevance_score": relevance_score,
                    "matching_reasons": matching_reasons,
                    "matched_technologies": matched_techs
                })
                print(f"   ✅ RELEVANT: {exp.get('role')} at {exp_company} ({years}y) - {matching_reasons}")
            else:
                non_matching_jobs.append({
                    "role": exp.get('role', 'Unknown'),
                    "company": exp_company,
                    "duration": exp_duration,
                    "years": years
                })
                print(f"   ❌ NOT RELEVANT: {exp.get('role')} at {exp_company} - No role/skill match")
        
        return (relevant_years, {
            "matching_jobs": matching_jobs,
            "matching_jobs_count": len(matching_jobs),
            "non_matching_jobs": non_matching_jobs
        })
    
    def _calculate_enhanced_experience_score_v2(
        self,
        resume_data: Dict,
        job_priorities: List[Dict],
        jd_experience_required: float,
        relevant_experience_years: float,
        relevance_details: Dict
    ) -> float:
        """
        Calculate experience score based ONLY on relevant experience
        
        Args:
            relevant_experience_years: Years of experience in matching roles
            relevance_details: Details about matching jobs
        """
        
        print(f"\n[ENHANCED EXPERIENCE SCORING V2]")
        print(f"   JD Required: {jd_experience_required} years")
        print(f"   Relevant Experience: {relevant_experience_years} years")
        
        # If no relevant experience, return 0
        if relevant_experience_years == 0:
            return 0.0
        
        # COMPONENT 1: Experience Requirement Match (50% weight)
        requirement_score = self._calculate_experience_requirement_score(
            relevant_experience_years, jd_experience_required
        )
        
        # COMPONENT 2: Quality of Relevant Experience (30% weight)
        quality_score = self._calculate_experience_quality_score(relevance_details)
        
        # COMPONENT 3: Recent/Current Relevant Experience Bonus (20% weight)
        recency_score = self._calculate_recent_experience_bonus_v2(
            resume_data.get('experience_timeline', []), job_priorities
        )
        
        # Final calculation
        final_score = (requirement_score * 0.5) + (quality_score * 0.3) + (recency_score * 0.2)
        
        print(f"   Score Breakdown:")
        print(f"      • Requirement Match: {requirement_score:.1f}/100 (50%)")
        print(f"      • Experience Quality: {quality_score:.1f}/100 (30%)")
        print(f"      • Recency Bonus: {recency_score:.1f}/100 (20%)")
        print(f"      • Final: {final_score:.1f}/100")
        
        return min(100, max(0, final_score))
    
    def _calculate_experience_quality_score(self, relevance_details: Dict) -> float:
        """Calculate quality score based on how well experience matches"""
        
        matching_jobs = relevance_details.get('matching_jobs', [])
        
        if not matching_jobs:
            return 0.0
        
        # Quality factors:
        # 1. Number of relevant jobs
        # 2. Average relevance score
        # 3. Diversity of matched technologies
        
        num_jobs = len(matching_jobs)
        avg_relevance = sum(job['relevance_score'] for job in matching_jobs) / num_jobs
        
        # All matched technologies across jobs
        all_matched_techs = set()
        for job in matching_jobs:
            all_matched_techs.update(job.get('matched_technologies', []))
        
        tech_diversity = len(all_matched_techs)
        
        # Scoring
        job_count_score = min(100, num_jobs * 25)  # 25 points per relevant job, max 100
        relevance_score = avg_relevance * 100
        tech_score = min(100, tech_diversity * 15)  # 15 points per unique tech, max 100
        
        quality_score = (job_count_score * 0.4) + (relevance_score * 0.4) + (tech_score * 0.2)
        
        return min(100, quality_score)
    
    def _calculate_recent_experience_bonus_v2(
        self, 
        experience_timeline: List[Dict], 
        job_priorities: List[Dict]
    ) -> float:
        """Calculate bonus for current/recent relevant experience"""
        
        if not experience_timeline:
            return 0.0
        
        current_year = datetime.now().year
        max_bonus = 0.0
        
        # Collect priority skills
        priority_skills = set()
        for priority in job_priorities:
            priority_skills.update([s.lower() for s in priority['key_skills']])
        
        for exp in experience_timeline:
            exp_duration = exp.get('duration', '').lower()
            exp_techs = [t.lower() for t in exp.get('technologies_used', [])]
            
            is_current = ('present' in exp_duration or 'current' in exp_duration)
            is_recent = any(str(year) in exp_duration for year in [current_year, current_year - 1])
            
            if is_current or is_recent:
                # Check if this current/recent experience is relevant
                matched_skills = sum(1 for skill in priority_skills if any(skill in tech for tech in exp_techs))
                
                if matched_skills > 0:
                    relevance_ratio = min(1.0, matched_skills / len(priority_skills))
                    
                    if is_current:
                        bonus = 100 * relevance_ratio
                    else:
                        bonus = 70 * relevance_ratio
                    
                    max_bonus = max(max_bonus, bonus)
        
        return max_bonus
    
    
    
    def _extract_experience_requirement(self, jd_data: Dict) -> float:
        # Extract experience requirement from job description
        
        # Source 1: Direct experience_required field
        if 'experience_required' in jd_data:
            exp_req = jd_data['experience_required']
            if isinstance(exp_req, (int, float)):
                return float(exp_req)
            elif isinstance(exp_req, str):
                parsed_exp = self._parse_experience_years(exp_req)
                if parsed_exp > 0:
                    return parsed_exp
        
        # Source 2: Parse from job title and description
        job_title = jd_data.get('job_title', '').lower()
        job_description = jd_data.get('description', '').lower()
        requirements = jd_data.get('requirements', [])
        
        all_text = f"{job_title} {job_description} {' '.join(requirements) if requirements else ''}"
        
        # Experience patterns
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*(?:of\s*)?exp',
            r'minimum\s*(\d+)\+?\s*years?',
            r'at\s*least\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\s*to\s*(\d+)\s*years?\s*experience',
            r'(\d+)-(\d+)\s*years?\s*experience'
        ]
        
        for pattern in exp_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                if isinstance(matches[0], tuple):
                    # Range like "2-5 years" take minimum
                    return float(matches[0][0])
                else:
                    # Single number like "3+ years"
                    return float(matches[0])
        
        # Default: No specific experience required
        return 0.0
    
    
    def _extract_resume_skills(self, resume_data: Dict) -> List[str]:
        # Extract Resume Skills
        
        skills = []
        
        # Source 1: Direct skills array
        if 'skills' in resume_data and isinstance(resume_data['skills'], list):
            skills.extend([skill.strip() for skill in resume_data['skills'] if skill.strip()])
        
        # Source 2: From structured data skills
        if 'structured_data' in resume_data and resume_data['structured_data']:
            structured_skills = resume_data['structured_data'].get('skills', [])
            if isinstance(structured_skills, list):
                skills.extend([skill.strip() for skill in structured_skills if skill.strip()])
        
        # Source 3: Extract from experience technologies
        experience_timeline = resume_data.get('experience_timeline', [])
        for experience in experience_timeline:
            tech_used = experience.get('technologies_used', [])
            if isinstance(tech_used, list):
                skills.extend([tech.strip() for tech in tech_used if tech.strip()])
        
        # Clean and deduplicate skills
        normalized_skills = []
        for skill in skills:
            if skill and len(skill.strip()) > 1:
                normalized_skill = self._normalize_skill(skill.strip())
                if normalized_skill not in normalized_skills:
                    normalized_skills.append(normalized_skill)
        
        return normalized_skills
    
    # Enhance Experience Data
    def _enhance_experience_data(self, resume_data: Dict, job_priorities: List[Dict]) -> List[Dict]:
        """Enhance experience data by analyzing job descriptions for technologies"""
        
        experience_timeline = resume_data.get('experience_timeline', [])
        enhanced_timeline = []
        
        # Collect all priority skills for matching
        all_priority_skills = []
        for priority in job_priorities:
            all_priority_skills.extend([skill.lower() for skill in priority.get('key_skills', [])])
        
        for experience in experience_timeline:
            enhanced_exp = experience.copy()
            
            # Get existing technologies
            existing_techs = set(tech.lower().strip() for tech in experience.get('technologies_used', []))
            
            # Analyze role title for technologies
            role_title = experience.get('role', '').lower()
            title_techs = self._extract_technologies_from_role_title(role_title)
            existing_techs.update(title_techs)
            
            # Analyze job description for technologies (if available)
            job_description = experience.get('description', '') or experience.get('responsibilities', '')
            if job_description:
                desc_techs = self._extract_technologies_from_description(job_description, all_priority_skills)
                existing_techs.update(desc_techs)
            
            # Update technologies used
            enhanced_exp['technologies_used'] = list(existing_techs)
            enhanced_timeline.append(enhanced_exp)
        
        return enhanced_timeline
    
    def _extract_technologies_from_role_title(self, role_title: str) -> List[str]:
        """Extract technologies from job role title"""
        
        title_tech_patterns = {
            'java': ['java developer', 'java engineer', 'j2ee', 'spring developer'],
            'python': ['python developer', 'python engineer', 'django developer', 'flask developer'],
            'javascript': ['javascript developer', 'js developer', 'frontend developer', 'react developer', 'angular developer'],
            'dotnet': ['.net developer', 'c# developer', 'asp.net developer'],
            'php': ['php developer', 'laravel developer'],
            'nodejs': ['node.js developer', 'nodejs developer', 'backend developer'],
            'react': ['react developer', 'reactjs developer'],
            'angular': ['angular developer', 'angularjs developer'],
            'spring': ['spring developer', 'spring boot developer'],
            'aws': ['aws developer', 'cloud developer', 'devops engineer'],
            'fullstack': ['full stack developer', 'fullstack developer'],
            'software development': ['software developer', 'software engineer', 'developer', 'engineer'],
            'Database' :['sql', 'mysql', 'postgresql', 'postgres', 'database']
        }
        
        found_techs = []
        role_lower = role_title.lower()
        
        for tech, patterns in title_tech_patterns.items():
            for pattern in patterns:
                if pattern in role_lower:
                    found_techs.append(tech)
                    break
        
        return found_techs
    
    def _extract_technologies_from_description(self, description: str, priority_skills: List[str]) -> List[str]:
        # Extracting technologies from job description text
        
        if not description:
            return []
        
        desc_lower = description.lower()
        found_techs = []
        
        # Enhanced technology patterns
        tech_patterns = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'java': ['java', 'spring', 'hibernate', 'maven', 'jsp', 'spring boot'],
            'javascript': ['javascript', 'js', 'node.js', 'nodejs', 'react', 'angular', 'vue'],
            'dotnet': ['.net', 'c#', 'asp.net', 'mvc', 'entity framework'],
            'php': ['php', 'laravel', 'codeigniter', 'symfony'],
            'databases': ['mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sql server'],
            'cloud': ['aws', 'azure', 'gcp', 'google cloud'],
            'devops': ['docker', 'kubernetes', 'jenkins', 'terraform', 'ci/cd'],
            'web': ['html', 'css', 'bootstrap', 'sass'],
            'mobile': ['android', 'ios', 'react native', 'flutter'],
            'tools': ['git', 'github', 'jira', 'postman'],
            'programming': ['programming', 'coding', 'development', 'software development']
        }
        
        # Searching for all technology patterns
        for category, techs in tech_patterns.items():
            for tech in techs:
                pattern = r'\b' + re.escape(tech.lower()) + r'\b'
                if re.search(pattern, desc_lower):
                    found_techs.append(tech)
        
        # Searching for priority skills specifically
        for skill in priority_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, desc_lower):
                found_techs.append(skill)
        
        # Remove duplicates
        return list(set(found_techs))
    
    # SCORE 1: Complete Skills Matching
    def _calculate_complete_skills_score(self, resume_data: Dict, job_priorities: List[Dict], skills_weightage: Dict) -> float:
        """Calculate skills score with enhanced matching (0-100 points)"""
        
        resume_skills = resume_data.get('skills', [])
        if not resume_skills:
            print("No skills found in resume - Skills Score: 0/100")
            return 0.0
        
        print(f"SKILLS SCORING:")
        
        # Collect ALL required skills from ALL priorities
        all_required_skills = []
        skill_metadata = {}
        
        for job_priority in job_priorities:
            key_skills = [skill.lower().strip() for skill in job_priority['key_skills']]
            priority_level = job_priority['priority']
            role_name = job_priority['role']
            
            for skill in key_skills:
                if skill not in skill_metadata:  # Avoid duplicates
                    all_required_skills.append(skill)
                    skill_metadata[skill] = {
                        'priority': priority_level,
                        'role': role_name,
                        'config_weight': skills_weightage.get(skill, 50)
                    }
        
        total_required_skills = len(all_required_skills)
        print(f"Total Skills Required: {total_required_skills}")
        
        if total_required_skills == 0:
            return 0.0
        
        # Enhanced skill matching
        total_weighted_score = 0
        total_possible_weight = 0
        matched_skills = []
        missing_skills = []
        
        for required_skill in all_required_skills:
            metadata = skill_metadata[required_skill]
            priority_level = metadata['priority']
            config_weight = metadata['config_weight'] / 100
            
            # Priority multipliers
            if priority_level == 1:
                priority_multiplier = 1.0    # 100% for 1st priority
            elif priority_level == 2:
                priority_multiplier = 0.85   # 85% for 2nd priority
            else:
                priority_multiplier = 0.70   # 70% for 3rd+ priority
            
            final_weight = config_weight * priority_multiplier
            total_possible_weight += final_weight
            
            # Enhanced skill matching
            has_skill = self._enhanced_candidate_has_skill(required_skill, resume_skills)
            
            if has_skill:
                total_weighted_score += final_weight
                matched_skills.append(required_skill)
                print(f"{required_skill} (P{priority_level}) - Weight: {final_weight:.3f}")
            else:
                missing_skills.append(required_skill)
                print(f"{required_skill} (P{priority_level}) - Missing")
        
        # Calculate base skills score
        if total_possible_weight == 0:
            base_skills_score = 0.0
        else:
            base_skills_score = (total_weighted_score / total_possible_weight) * 100
        
        # Coverage bonuses
        coverage_ratio = len(matched_skills) / total_required_skills
        
        if coverage_ratio >= 0.95:
            coverage_bonus = 15
        elif coverage_ratio >= 0.90:
            coverage_bonus = 10
        elif coverage_ratio >= 0.80:
            coverage_bonus = 5
        else:
            coverage_bonus = 0
        
        # Priority 1 skills bonus
        priority1_skills = [s for s in all_required_skills if skill_metadata[s]['priority'] == 1]
        priority1_matched = [s for s in matched_skills if skill_metadata[s]['priority'] == 1]
        
        if len(priority1_skills) > 0:
            priority1_coverage = len(priority1_matched) / len(priority1_skills)
            if priority1_coverage == 1.0:  # 100% of priority 1 skills
                priority_bonus = 10
            elif priority1_coverage >= 0.8:  # 80%+ of priority 1 skills
                priority_bonus = 5
            else:
                priority_bonus = 0
        else:
            priority_bonus = 0
        
        # Final skills score
        final_skills_score = min(100, base_skills_score + coverage_bonus + priority_bonus)
        
        print(f"Skills: {len(matched_skills)}/{total_required_skills} matched ({coverage_ratio*100:.1f}%)")
        print(f"Score: {base_skills_score:.1f} + {coverage_bonus} + {priority_bonus} = {final_skills_score:.1f}/100")
        
        return final_skills_score
    

    def _calculate_experience_requirement_score(
        self,
        total_experience: float,
        jd_experience_required: float
    ) -> float:

        print("\n[Experience Requirement Scoring]")
        print(f"   Candidate Experience: {total_experience} years")
        print(f"   JD Required Experience: {jd_experience_required} years")

        # Safety check — handle None or invalid values
        if total_experience is None:
            total_experience = 0.0
        if jd_experience_required is None:
            jd_experience_required = 0.0

        # CASE 1: JD doesn’t specify experience requirement
        if jd_experience_required == 0:
            print("No required experience — scoring based on candidate experience only.")
            if total_experience == 0:
                score = 60.0  # Neutral for fresh graduates
            elif total_experience >= 5:
                score = 95.0  # Excellent for 5+ years
            elif total_experience >= 3:
                score = 85.0  # Very good for 3–5 years
            elif total_experience >= 2:
                score = 75.0  # Good for 2–3 years
            elif total_experience >= 1:
                score = 70.0  # Moderate for 1–2 years
            else:
                score = 65.0  # Acceptable for <1 year
            print(f"Score: {score}/100")
            return score

        # CASE 2: JD specifies experience requirement
        else:
            # Exceeds requirement by 50%+
            if total_experience >= jd_experience_required * 1.5:
                score = 100.0
                print(f"Exceeds requirement significantly — Score: {score}/100")
                return score

            # Meets or slightly exceeds requirement (100–150%)
            elif total_experience >= jd_experience_required:
                excess_ratio = (total_experience - jd_experience_required) / (jd_experience_required * 0.5)
                score = min(100.0, 85 + (excess_ratio * 15))
                print(f"Meets or exceeds requirement — Score: {score}/100")
                return score

            # 80–100% of requirement (close match)
            elif total_experience >= jd_experience_required * 0.8:
                ratio = total_experience / jd_experience_required
                score = 60 + ((ratio - 0.8) * 125)  # scales between 60–85
                print(f"80-100% of requirement — Score: {score}/100")
                return score

            # 50–80% of requirement
            elif total_experience >= jd_experience_required * 0.5:
                ratio = total_experience / jd_experience_required
                score = 30 + ((ratio - 0.5) * 100)  # scales between 30–60
                print(f" 50-80% of requirement — Score: {score}/100")
                return score

            # Below 50% of requirement but has some experience
            elif total_experience > 0:
                ratio = total_experience / jd_experience_required
                score = max(10.0, ratio * 60)  # ensures non-zero score
                print(f"Below 50% requirement — Score: {score}/100")
                return score

            # No experience when experience is required
            else:
                score = 10.0  # minimal score to avoid 0%
                print(f"No experience for required JD — Score: {score}/100")
                return score

        
    
    def _calculate_enhanced_experience_score(self, resume_data: Dict, job_priorities: List[Dict], jd_experience_required: float) -> float:
        """Calculate enhanced experience score"""
        
        experience_timeline = resume_data.get("experience_timeline", [])
        total_experience = resume_data.get("total_experience", 0)
        
        print(f"[ENHANCED EXPERIENCE SCORING]")
        print(f"   Total Experience: {total_experience} years")
        print(f"   JD Required Experience: {jd_experience_required} years")
        print(f"   Experience Timeline: {len(experience_timeline)} jobs")
        
        # Handle fresh graduates
        if not experience_timeline or total_experience == 0:
            if jd_experience_required == 0:
                print("   Fresh Graduate - No Experience Required: 50/100")
                return 50.0  # Neutral score
            else:
                print("   Fresh Graduate but Experience Required: 10/100")
                return 10.0  # Low score when experience is required
        
        # STEP 1: Experience Requirement Matching Score (40% weight)
        experience_requirement_score = self._calculate_experience_requirement_score(total_experience, jd_experience_required)
        
        # STEP 2: Relevant Experience Score (40% weight)
        relevant_experience_score = self._calculate_relevant_experience_score(experience_timeline, job_priorities)
        
        # STEP 3: Recent/Current Experience Bonus (20% weight)
        recent_experience_bonus = self._calculate_recent_experience_bonus(experience_timeline, job_priorities)
        
        # Final experience score calculation
        final_experience_score = (
            (experience_requirement_score * 0.4) +
            (relevant_experience_score * 0.4) +
            (recent_experience_bonus * 0.2)
        )
        
        print(f"   Experience Breakdown:")
        print(f"      • Requirement Match: {experience_requirement_score:.1f}/100 (40% weight)")
        print(f"      • Relevant Experience: {relevant_experience_score:.1f}/100 (40% weight)")
        print(f"      • Recent/Current Bonus: {recent_experience_bonus:.1f}/100 (20% weight)")
        print(f"      • Final Experience Score: {final_experience_score:.1f}/100")
        
        return min(100, max(0, final_experience_score))


    def _calculate_relevant_experience_score(self, experience_timeline: List[Dict], job_priorities: List[Dict]) -> float:
        """Calculate score based on relevant experience in priority technologies"""
        
        if not experience_timeline or not job_priorities:
            return 0.0
        
        # Consider TOP 2 priorities only
        top_priorities = sorted(job_priorities, key=lambda x: x['priority'])[:2]
        
        priority_scores = []
        
        for job_priority in top_priorities:
            role_name = job_priority['role']
            key_skills = job_priority['key_skills']
            priority_level = job_priority['priority']
            
            total_relevant_years = 0
            matched_experiences = []
            
            for experience in experience_timeline:
                exp_role = experience.get('role', '').lower()
                exp_technologies = [tech.lower().strip() for tech in experience.get('technologies_used', [])]
                exp_duration = experience.get('duration', '')
                exp_company = experience.get('company', '')
                
                # Calculate years
                years = self._extract_years_from_duration(exp_duration)
                
                # Multi-level relevance calculation
                matched_technologies = []
                role_match_score = 0
                description_matches = 0
                
                # Level 1: Direct technology matching
                for skill in key_skills:
                    skill_lower = skill.lower().strip()
                    
                    for tech in exp_technologies:
                        tech_lower = tech.lower().strip()
                        
                        if self._enhanced_technology_match(skill_lower, tech_lower):
                            matched_technologies.append(skill)
                            break
                
                # Level 2: Role title matching (enhanced)
                role_keywords = role_name.lower().replace(' developer', '').replace(' engineer', '').replace(' analyst', '').split()
                for keyword in role_keywords:
                    if keyword in exp_role:
                        # More specific matches get higher scores
                        if keyword in ['python', 'java', 'javascript', 'react', 'angular', '.net', 'php', 'business', 'analyst']:
                            role_match_score += 2  # Technology/role-specific
                        elif keyword not in ['developer', 'engineer', 'software', 'senior', 'junior']:
                            role_match_score += 1  # Other relevant keywords
                
                # Level 3: Job description analysis (if available)
                job_description = experience.get('description', '') or experience.get('responsibilities', '')
                if job_description:
                    desc_lower = job_description.lower()
                    for skill in key_skills:
                        if skill.lower() in desc_lower:
                            description_matches += 1
                
                # Multi-factor relevance calculation
                tech_relevance = len(matched_technologies) / len(key_skills) if key_skills else 0
                role_relevance = min(1.0, role_match_score * 0.25)  # Up to 100% from role matching
                desc_relevance = min(0.3, description_matches * 0.1)  # Up to 30% from description
                
                overall_relevance = tech_relevance + role_relevance + desc_relevance
                
                # LOWERED THRESHOLD: More inclusive matching
                if overall_relevance > 0.05:  # Very low threshold for inclusivity
                    # Experience quality multiplier
                    quality_multiplier = 1.0
                    
                    # Bonus for current/recent experience
                    if 'present' in exp_duration.lower() or 'current' in exp_duration.lower():
                        quality_multiplier += 0.3  # 30% bonus for current roles
                    
                    # Bonus for high relevance
                    if overall_relevance > 0.8:
                        quality_multiplier += 0.2  # 20% bonus for high relevance
                    elif overall_relevance > 0.5:
                        quality_multiplier += 0.1  # 10% bonus for good relevance
                    
                    # Calculate weighted years
                    weighted_years = years * min(2.0, overall_relevance * quality_multiplier)  # Cap at 2x
                    total_relevant_years += weighted_years
                    
                    matched_experiences.append({
                        'company': exp_company,
                        'role': experience.get('role', ''),
                        'years': years,
                        'weighted_years': weighted_years,
                        'relevance': overall_relevance,
                        'quality_multiplier': quality_multiplier,
                        'matched_techs': matched_technologies
                    })
            
            # Dynamic scoring based on experience levels
            if priority_level == 1:  # 1st Priority - MAXIMUM SCORING
                if total_relevant_years >= 7:
                    base_score = 100  # Exceptional experience
                elif total_relevant_years >= 5:
                    base_score = 90 + ((total_relevant_years - 5) * 5)  # 90-100%
                elif total_relevant_years >= 3:
                    base_score = 75 + ((total_relevant_years - 3) * 7.5)  # 75-90%
                elif total_relevant_years >= 2:
                    base_score = 60 + ((total_relevant_years - 2) * 15)  # 60-75%
                elif total_relevant_years >= 1:
                    base_score = 40 + ((total_relevant_years - 1) * 20)  # 40-60%
                elif total_relevant_years > 0:
                    base_score = 20 + (total_relevant_years * 20)  # 20-40%
                else:
                    base_score = 5
                
                # Additional bonuses for Priority 1
                if len(matched_experiences) >= 2:
                    base_score += 10  # Bonus for multiple relevant experiences
                
                priority_score = base_score * 0.7  # 70% weight
                    
            else:  # 2nd Priority
                if total_relevant_years >= 5:
                    base_score = 95
                elif total_relevant_years >= 3:
                    base_score = 80 + ((total_relevant_years - 3) * 7.5)  # 80-95%
                elif total_relevant_years >= 2:
                    base_score = 65 + ((total_relevant_years - 2) * 15)  # 65-80%
                elif total_relevant_years >= 1:
                    base_score = 45 + ((total_relevant_years - 1) * 20)  # 45-65%
                elif total_relevant_years > 0:
                    base_score = 25 + (total_relevant_years * 20)  # 25-45%
                else:
                    base_score = 3
                
                priority_score = base_score * 0.3  # 30% weight
            
            priority_scores.append(priority_score)
        
        final_score = sum(priority_scores)
        
        # BONUS Multi-priority experience
        if len(priority_scores) == 2 and all(score > 5 for score in priority_scores):
            multi_bonus = min(15, priority_scores[0] * 0.1 + priority_scores[1] * 0.2)
            final_score += multi_bonus
        
        return min(100, final_score)

    def _calculate_recent_experience_bonus(self, experience_timeline: List[Dict], job_priorities: List[Dict]) -> float:
        # Calculate bonus for recent or current experience in priority technologies
        
        if not experience_timeline or not job_priorities:
            return 0.0
        
        current_year = datetime.now().year
        max_bonus = 0
        
        for experience in experience_timeline:
            exp_duration = experience.get('duration', '').lower()
            exp_technologies = [tech.lower().strip() for tech in experience.get('technologies_used', [])]
            
            #checking
            is_current = ('present' in exp_duration or 'current' in exp_duration)
            is_recent = any(str(year) in exp_duration for year in [current_year, current_year-1])
            
            if is_current or is_recent:
                # Check relevance to priorities
                for job_priority in job_priorities:
                    key_skills = job_priority['key_skills']
                    priority_level = job_priority['priority']
                    
                    matched_skills = 0
                    for skill in key_skills:
                        for tech in exp_technologies:
                            if self._enhanced_technology_match(skill.lower(), tech.lower()):
                                matched_skills += 1
                                break
                    
                    if matched_skills > 0:
                        relevance_ratio = matched_skills / len(key_skills)
                        
                        if is_current:
                            if priority_level == 1:
                                bonus = 100 * relevance_ratio
                            else:
                                bonus = 70 * relevance_ratio
                        else:  # is_recent
                            if priority_level == 1:
                                bonus = 70 * relevance_ratio
                            else:
                                bonus = 50 * relevance_ratio
                        
                        max_bonus = max(max_bonus, bonus)
        
        return max_bonus
    
    # Helper Methods
    def _enhanced_candidate_has_skill(self, target_skill: str, resume_skills: List[str]) -> bool:
        # Enhanced skill matching
        
        target_normalized = self._normalize_skill(target_skill)
        
        for resume_skill in resume_skills:
            resume_normalized = self._normalize_skill(resume_skill)
            
            # Exact match
            if target_normalized == resume_normalized:
                return True
            
            # Synonym match
            if self._enhanced_skill_synonym_match(target_normalized, resume_normalized):
                return True
            
            # Partial match
            if target_normalized in resume_normalized or resume_normalized in target_normalized:
                return True
            
            # Fuzzy match
            if self._fuzzy_skill_match(target_normalized, resume_normalized):
                return True
        
        return False
    
    def _enhanced_technology_match(self, required_tech: str, resume_tech: str) -> bool:
        # Enhanced technology matching
        
        # Direct match
        if required_tech == resume_tech:
            return True
        
        # Enhanced technology synonyms
        tech_synonyms = {
            'java': ['java', 'core java', 'spring boot', 'spring framework', 'hibernate', 'jsp', 'j2ee', 'spring'],
            'python': ['python', 'django', 'flask', 'fastapi', 'python3', 'py'],
            'javascript': ['javascript', 'js', 'node.js', 'nodejs', 'react', 'angular', 'vue', 'jquery'],
            'spring': ['spring', 'spring boot', 'spring framework', 'springframework'],
            'react': ['react', 'reactjs', 'react.js'],
            'angular': ['angular', 'angularjs', 'angular.js'],
            'dotnet': ['.net', 'c#', 'asp.net', 'dotnet', '.net core'],
            'mysql': ['mysql', 'my sql', 'Database'],
            'postgresql': ['postgresql', 'postgres', 'psql'],
            'mongodb': ['mongodb', 'mongo', 'mongo db'],
            'aws': ['aws', 'amazon web services'],
            'docker': ['docker', 'containerization'],
            'git': ['git', 'github', 'gitlab', 'version control'],
            'programming': ['programming', 'coding', 'development', 'software development'],
            'software development': ['software development', 'development', 'programming', 'coding']
        }
        
        # Check synonym groups
        for canonical, variations in tech_synonyms.items():
            if required_tech in variations and resume_tech in variations:
                return True
        
        # Partial matching
        if required_tech in resume_tech or resume_tech in required_tech:
            return True
        
        return False
    
    def _enhanced_skill_synonym_match(self, skill1: str, skill2: str) -> bool:
        # Enhanced synonym matching for skills
        
        enhanced_synonyms = {
            'java': ['java', 'core java', 'java se', 'java ee', 'j2ee', 'openjdk'],
            'python': ['python', 'python3', 'py', 'cpython'],
            'javascript': ['javascript', 'js', 'ecmascript', 'es6', 'es2015'],
            'react': ['react', 'reactjs', 'react.js'],
            'angular': ['angular', 'angularjs', 'angular.js', 'angular2+'],
            'spring': ['spring', 'spring boot', 'spring framework'],
            'nodejs': ['node.js', 'nodejs', 'node'],
            'dotnet': ['.net', 'dotnet', 'dot net', '.net framework', '.net core'],
            'csharp': ['c#', 'csharp', 'c sharp'],
            'mysql': ['mysql', 'my sql', 'database'],
            'postgresql': ['postgresql', 'postgres', 'psql'],
            'mongodb': ['mongodb', 'mongo'],
            'html': ['html', 'html5'],
            'css': ['css', 'css3'],
            'aws': ['aws', 'amazon web services'],
            'azure': ['azure', 'microsoft azure'],
            'docker': ['docker', 'containerization'],
            'kubernetes': ['kubernetes', 'k8s'],
            'programming': ['programming', 'coding', 'development', 'software development'],
            'software development': ['software development', 'development', 'programming', 'coding']
        }
        
        for canonical, variations in enhanced_synonyms.items():
            if skill1 in variations and skill2 in variations:
                return True
        
        return False
    
    def _fuzzy_skill_match(self, skill1: str, skill2: str) -> bool:
        # Fuzzy matching for skills
        
        if len(skill1) < 3 or len(skill2) < 3:
            return False
        
        # Character overlap ratio
        overlap = len(set(skill1) & set(skill2))
        min_length = min(len(skill1), len(skill2))
        
        if overlap / min_length > 0.8:
            return True
        
        # spaCy semantic similarity
        if self.nlp:
            try:
                doc1 = self.nlp(skill1)
                doc2 = self.nlp(skill2)
                similarity = doc1.similarity(doc2)
                return similarity > 0.85 
            except:
                pass
        
        return False
    
    def _normalize_skill(self, skill: str) -> str:
        # Normalize skill for consistent matching
        
        if not isinstance(skill, str):
            return str(skill).lower().strip()
        
        # Clean the skill
        skill = re.sub(r'[^\w\s+#.]', '', skill.lower().strip())
        
        # Remove common suffixes
        skill = re.sub(r'\s+(framework|js|developer|development)$', '', skill)
        
        return skill
    
    # Analysis Methods
    def _get_complete_skills_analysis(self, resume_data: Dict, job_priorities: List[Dict], skills_weightage: Dict) -> Dict:
        """Detailed skills analysis"""
        
        resume_skills = resume_data.get('skills', [])
        
        analysis = {
            'total_resume_skills': len(resume_skills),
            'resume_skills': resume_skills[:20], 
            'priorities': [],
            'overall_summary': {}
        }
        
        total_required = 0
        total_matched = 0
        
        for job_priority in job_priorities:
            key_skills = [skill.lower().strip() for skill in job_priority['key_skills']]
            priority_level = job_priority['priority']
            role_name = job_priority['role']
            
            matched_skills = []
            missing_skills = []
            
            for skill in key_skills:
                has_skill = self._enhanced_candidate_has_skill(skill, resume_skills)
                config_weight = skills_weightage.get(skill, 50)
                
                if has_skill:
                    matched_skills.append(skill)
                    total_matched += 1
                else:
                    missing_skills.append(skill)
                
                total_required += 1
            
            coverage = (len(matched_skills) / len(key_skills)) * 100 if key_skills else 0
            
            analysis['priorities'].append({
                'priority_level': priority_level,
                'role_name': role_name,
                'total_skills': len(key_skills),
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'coverage_percentage': round(coverage, 1)
            })
        
        overall_coverage = (total_matched / total_required) * 100 if total_required > 0 else 0
        
        analysis['overall_summary'] = {
            'total_skills_required': total_required,
            'total_skills_matched': total_matched,
            'overall_coverage': round(overall_coverage, 1)
        }
        
        return analysis
    
    def _get_enhanced_experience_analysis(self, resume_data: Dict, job_priorities: List[Dict], jd_experience_required: float) -> Dict:
        # Enhanced experience analysis with JD requirement matching
        
        experience_timeline = resume_data.get('experience_timeline', [])
        total_experience = resume_data.get('total_experience', 0)
        
        analysis = {
            'total_experience': total_experience,
            'jd_experience_required': jd_experience_required,
            'meets_requirement': total_experience >= jd_experience_required,
            'experience_gap': max(0, jd_experience_required - total_experience),
            'experience_excess': max(0, total_experience - jd_experience_required),
            'total_jobs': len(experience_timeline),
            'is_fresh_graduate': total_experience == 0 or not experience_timeline,
            'top_priorities': []
        }
        
        top_priorities = sorted(job_priorities, key=lambda x: x['priority'])[:2]
        
        for job_priority in top_priorities:
            key_skills = job_priority['key_skills']
            priority_level = job_priority['priority']
            role_name = job_priority['role']
            
            relevant_experiences = []
            total_years = 0
            current_experience = None
            
            for experience in experience_timeline:
                exp_technologies = [tech.lower().strip() for tech in experience.get('technologies_used', [])]
                matched_techs = []
                
                for skill in key_skills:
                    for tech in exp_technologies:
                        if self._enhanced_technology_match(skill.lower(), tech):
                            matched_techs.append(skill)
                            break
                
                if matched_techs:
                    years = self._extract_years_from_duration(experience.get('duration', ''))
                    total_years += years
                    is_current = 'present' in experience.get('duration', '').lower()
                    
                    exp_data = {
                        'company': experience.get('company', ''),
                        'role': experience.get('role', ''),
                        'duration': experience.get('duration', ''),
                        'years': years,
                        'matched_technologies': matched_techs,
                        'is_current': is_current
                    }
                    
                    relevant_experiences.append(exp_data)
                    
                    if is_current:
                        current_experience = exp_data
            
            experience_strength = self._categorize_experience_strength(total_years, priority_level)
            
            analysis['top_priorities'].append({
                'priority_level': priority_level,
                'role_name': role_name,
                'total_years': round(total_years, 1),
                'relevant_experiences': relevant_experiences,
                'current_experience': current_experience,
                'experience_strength': experience_strength
            })
        
        return analysis
    
    def _categorize_experience_strength(self, years: float, priority_level: int) -> str:
        # Categorize experience strength
        if priority_level == 1:
            if years >= 5:
                return "Excellent"
            elif years >= 3:
                return "Very Good"
            elif years >= 2:
                return "Good"
            elif years >= 1:
                return "Moderate"
            else:
                return "Limited"
        else:
            if years >= 3:
                return "Very Good"
            elif years >= 2:
                return "Good"
            elif years >= 1:
                return "Moderate"
            else:
                return "Limited"
    
    # Utility Methods
    def _extract_job_priorities(self, jd_data: Dict, manual_priorities: List[Dict] = None) -> List[Dict]:
        """Extract job priorities"""
        if manual_priorities and len(manual_priorities) > 0:
            print(f"Using MANUAL priorities: {len(manual_priorities)} specified")
            return manual_priorities
        
        print(f"Using AUTO-DETECTED priorities")
        return self._auto_detect_job_priorities(jd_data)
    
    def _auto_detect_job_priorities(self, jd_data: Dict) -> List[Dict]:
        # Auto-detect priorities from JD dynamically based on actual requirements
        
        job_title = jd_data.get('job_title', '').lower()
        job_description = jd_data.get('description', '').lower()
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        
        all_text = f"{job_title} {job_description}"
        priorities = []
        
        # DYNAMIC ROLE DETECTION All roles compete for Priority 1
        role_detection_patterns = [
           
    {
        'role': 'Python Developer',
        'key_skills': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
        'patterns': ['python developer', 'python', 'django', 'flask', 'fastapi'],
        'weight': 1.0
    },
    {
        'role': 'Java Developer',
        'key_skills': ['java', 'spring', 'hibernate', 'jsp', 'maven', 'spring boot'],
        'patterns': ['java developer', 'java', 'spring', 'j2ee', 'jsp', 'spring boot'],
        'weight': 1.0
    },
    {
        'role': '.NET Developer',
        'key_skills': ['c#', '.net', 'asp.net', 'sql server', 'mvc', 'entity framework'],
        'patterns': ['.net developer', '.net', 'dotnet', 'c#', 'asp.net', 'mvc'],
        'weight': 1.0
    },
    {
        'role': 'JavaScript Developer',
        'key_skills': ['javascript', 'react', 'angular', 'vue', 'node.js', 'express'],
        'patterns': ['javascript developer', 'js developer', 'react developer', 'angular developer', 'node.js', 'frontend developer'],
        'weight': 1.0
    },
    {
        'role': 'PHP Developer',
        'key_skills': ['php', 'laravel', 'codeigniter', 'symfony', 'mysql', 'wordpress'],
        'patterns': ['php developer', 'php', 'laravel', 'codeigniter', 'wordpress'],
        'weight': 1.0
    },
    {
        'role': 'Ruby Developer',
        'key_skills': ['ruby', 'ruby on rails', 'rails', 'rspec', 'postgresql'],
        'patterns': ['ruby developer', 'ruby', 'rails', 'ruby on rails'],
        'weight': 1.0
    },
    {
        'role': 'Go Developer',
        'key_skills': ['go', 'golang', 'gin', 'gorilla', 'postgresql', 'redis'],
        'patterns': ['go developer', 'golang developer', 'go', 'golang'],
        'weight': 1.0
    },
    {
        'role': 'DevOps Engineer',
        'key_skills': ['docker', 'kubernetes', 'jenkins', 'terraform', 'aws', 'azure'],
        'patterns': ['devops engineer', 'devops', 'infrastructure engineer', 'cloud engineer', 'docker', 'kubernetes'],
        'weight': 1.0
    },
    {
        'role': 'Data Scientist',
        'key_skills': ['python', 'machine learning', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
        'patterns': ['data scientist', 'machine learning engineer', 'ml engineer', 'data analyst'],
        'weight': 1.0
    },
    {
        'role': 'Mobile Developer',
        'key_skills': ['android', 'ios', 'react native', 'flutter', 'swift', 'kotlin'],
        'patterns': ['mobile developer', 'android developer', 'ios developer', 'react native', 'flutter'],
        'weight': 1.0
    },
    {
        'role': 'Full Stack Developer',
        'key_skills': ['javascript', 'react', 'node.js', 'python', 'django', 'postgresql'],
        'patterns': ['full stack developer', 'fullstack developer', 'full-stack developer'],
        'weight': 1.0
    },
    {
        'role': 'Frontend Developer',
        'key_skills': ['html', 'css', 'javascript', 'react', 'angular', 'vue'],
        'patterns': ['frontend developer', 'front-end developer', 'ui developer', 'web developer'],
        'weight': 1.0
    },
    {
        'role': 'Backend Developer',
        'key_skills': ['api', 'database', 'microservices', 'rest', 'sql', 'nosql'],
        'patterns': ['backend developer', 'back-end developer', 'api developer', 'server developer'],
        'weight': 1.0
    },
    {
        'role': 'QA Engineer',
        'key_skills': ['testing', 'automation', 'selenium', 'junit', 'pytest', 'cypress'],
        'patterns': ['qa engineer', 'quality assurance', 'test engineer', 'automation engineer'],
        'weight': 1.0
    },
    {
        'role': 'Business Analyst',
        'key_skills': ['business analysis', 'requirement gathering', 'stakeholder management', 'documentation', 'process analysis', 'data analysis'],
        'patterns': ['business analyst', 'ba ', 'requirements analyst', 'systems analyst', 'process analyst'],
        'weight': 1.0
    },
    {
        'role': 'Project Manager',
        'key_skills': ['project management', 'agile', 'scrum', 'stakeholder management', 'planning', 'coordination'],
        'patterns': ['project manager', 'program manager', 'delivery manager', 'scrum master'],
        'weight': 1.0
    },
    {
        'role': 'Data Analyst',
        'key_skills': ['data analysis', 'excel', 'power bi', 'sql', 'reporting', 'dashboard'],
        'patterns': ['data analyst', 'business intelligence', 'reporting analyst', 'data scientist'],
        'weight': 1.0
    },
    {
        'role': 'Cloud Engineer',
        'key_skills': ['aws', 'azure', 'gcp', 'cloudformation', 'terraform', 'cloud architecture'],
        'patterns': ['cloud engineer', 'aws engineer', 'azure engineer', 'cloud solutions architect', 'gcp engineer'],
        'weight': 1.0
    },
    {
        'role': 'AI/ML Engineer',
        'key_skills': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp'],
        'patterns': ['ai engineer', 'ml engineer', 'machine learning engineer', 'deep learning engineer'],
        'weight': 1.0
    },
    {
        'role': 'Cybersecurity Engineer',
        'key_skills': ['security', 'network security', 'penetration testing', 'firewalls', 'siem', 'vulnerability assessment'],
        'patterns': ['cybersecurity', 'security engineer', 'information security', 'infosec', 'network security'],
        'weight': 1.0
    },
    {
        'role': 'UI/UX Designer',
        'key_skills': ['ux', 'ui', 'figma', 'adobe xd', 'prototyping', 'user research'],
        'patterns': ['ui designer', 'ux designer', 'ui/ux', 'user experience designer', 'interaction designer'],
        'weight': 1.0
    },
    {
        'role': 'Database Administrator',
        'key_skills': ['sql', 'oracle', 'mysql', 'postgresql', 'database administration', 'performance tuning'],
        'patterns': ['dba', 'database administrator', 'sql dba', 'oracle dba'],
        'weight': 1.0
    },
    {
        'role': 'Site Reliability Engineer',
        'key_skills': ['sre', 'monitoring', 'incident management', 'prometheus', 'grafana', 'reliability engineering'],
        'patterns': ['site reliability engineer', 'sre', 'system reliability', 'infrastructure reliability'],
        'weight': 1.0
    },
    {
        'role': 'System Administrator',
        'key_skills': ['linux', 'windows server', 'networking', 'bash', 'powershell', 'active directory'],
        'patterns': ['system administrator', 'sysadmin', 'windows admin', 'linux admin'],
        'weight': 1.0
    },
    {
        'role': 'Game Developer',
        'key_skills': ['unity', 'unreal engine', 'c++', 'c#', 'game design', '3d graphics'],
        'patterns': ['game developer', 'unity developer', 'unreal developer', 'game programmer'],
        'weight': 1.0
    },
    {
        'role': 'Blockchain Developer',
        'key_skills': ['solidity', 'ethereum', 'smart contracts', 'web3', 'blockchain', 'nfts'],
        'patterns': ['blockchain developer', 'smart contract developer', 'solidity', 'web3 developer'],
        'weight': 1.0
    },
    {
        'role': 'Embedded Systems Engineer',
        'key_skills': ['embedded c', 'firmware', 'microcontrollers', 'rtos', 'iot', 'c++'],
        'patterns': ['embedded engineer', 'embedded systems', 'firmware engineer', 'iot developer'],
        'weight': 1.0
    }, {
    'role': 'ETL Developer',
    'key_skills': ['etl', 'informatica', 'data warehousing', 'ssis', 'data pipelines', 'sql'],
    'patterns': ['etl developer', 'data warehouse developer', 'data integration', 'ssis developer'],
    'weight': 1.0
    },
    {
    'role': 'Product Architect',
    'key_skills': ['product architecture', 'system design', 'product strategy', 'technical leadership', 'requirement analysis'],
    'patterns': ['product architect', 'product architecture', 'technical product architect'],
    'weight': 1.0
    },
    {
    'role': 'Software Architect',
    'key_skills': ['software architecture', 'system design', 'microservices', 'design patterns', 'scalability', 'performance tuning'],
    'patterns': ['software architect', 'technical architect', 'solution designer', 'system architect'],
    'weight': 1.0
    },
    {
        'role': 'Business Development Executive',
        'key_skills': ['business development', 'sales', 'lead generation', 'client acquisition', 'negotiation', 'partnerships'],
        'patterns': ['business development executive', 'bde', 'business development', 'sales executive', 'client acquisition'],
        'weight': 1.0
    },
    {
        'role': 'Sales Executive',
        'key_skills': ['sales', 'lead generation', 'cold calling', 'negotiation', 'crm', 'relationship management'],
        'patterns': ['sales executive', 'sales associate', 'sales representative', 'sales manager'],
        'weight': 1.0
    },
    {
        'role': 'Business Associate',
        'key_skills': ['business development', 'market research', 'sales', 'partnerships', 'communication'],
        'patterns': ['business associate', 'business partner', 'associate - business development'],
        'weight': 1.0
    },
    {
        'role': 'MERN Stack Developer',
        'key_skills': ['mongodb', 'express', 'react', 'node.js', 'javascript', 'fullstack'],
        'patterns': ['mern stack developer', 'mern developer', 'mern'],
        'weight': 1.0
    },
    {
        'role': 'Quality Analyst',
        'key_skills': ['quality analysis', 'manual testing', 'automation testing', 'bug tracking', 'test cases'],
        'patterns': ['quality analyst', 'qa analyst', 'quality analysis', 'qa tester'],
        'weight': 1.0
    },
    {
        'role': 'Graphic Designer',
        'key_skills': ['graphic design', 'photoshop', 'illustrator', 'corel draw', 'creativity', 'branding'],
        'patterns': ['graphic designer', 'visual designer', 'graphics', 'creative designer'],
        'weight': 1.0
    },
    {
        'role': 'Android Developer',
        'key_skills': ['android', 'java', 'kotlin', 'mobile apps', 'android studio'],
        'patterns': ['android developer', 'android engineer', 'mobile android'],
        'weight': 1.0
    },
    {
        'role': 'Flutter Developer',
        'key_skills': ['flutter', 'dart', 'mobile development', 'cross-platform', 'firebase'],
        'patterns': ['flutter developer', 'flutter engineer', 'flutter mobile'],
        'weight': 1.0
    },
    {
        'role': 'React Native Developer',
        'key_skills': ['react native', 'javascript', 'mobile apps', 'ios', 'android'],
        'patterns': ['react native developer', 'rn developer', 'reactnative'],
        'weight': 1.0
    },
    {
        'role': 'Laravel Developer',
        'key_skills': ['php', 'laravel', 'mysql', 'eloquent', 'backend development'],
        'patterns': ['laravel developer', 'php laravel', 'laravel'],
        'weight': 1.0
    },
    {
        'role': 'Office Administrative Executive',
        'key_skills': ['administration', 'office management', 'coordination', 'documentation', 'ms office'],
        'patterns': ['administrative executive', 'office executive', 'admin executive', 'office administrator'],
        'weight': 1.0
    },
    {
        'role': 'Sales and Marketing Executive',
        'key_skills': ['sales', 'marketing', 'digital marketing', 'business development', 'crm', 'advertising'],
        'patterns': ['sales and marketing executive', 'sales & marketing', 'marketing executive'],
        'weight': 1.0
    },
    {
        'role': 'Blue Prism Developer',
        'key_skills': ['rpa', 'blue prism', 'automation', 'process automation', 'bots'],
        'patterns': ['blue prism developer', 'rpa blue prism', 'automation developer'],
        'weight': 1.0
    },
    {
        'role': 'Database Management Specialist',
        'key_skills': ['database management', 'sql', 'mysql', 'oracle', 'postgresql', 'data migration'],
        'patterns': ['database management', 'dbms specialist', 'database support'],
        'weight': 1.0
    }, 
    {
    'role': 'Mechanical Engineer',
    'key_skills': ['autocad', 'solidworks', 'catia', 'cad', 'manufacturing', 'design', 'mechanical design', 'thermodynamics', 'fluid mechanics'],
    'patterns': ['mechanical engineer', 'mechanical', 'manufacturing engineer', 'design engineer'],
    'weight': 1.0
},
{
    'role': 'Civil Engineer',
    'key_skills': ['autocad', 'civil 3d', 'structural design', 'construction', 'surveying', 'site planning', 'structural analysis', 'revit'],
    'patterns': ['civil engineer', 'civil engineering', 'structural engineer', 'construction engineer', 'site engineer'],
    'weight': 1.0
},
{
    'role': 'Electrical Engineer',
    'key_skills': ['circuit design', 'pcb design', 'plc', 'scada', 'electrical systems', 'power systems', 'autocad electrical', 'matlab'],
    'patterns': ['electrical engineer', 'electrical', 'power engineer', 'electronics engineer'],
    'weight': 1.0
},
{
    'role': 'Aeronautical Engineer',
    'key_skills': ['aerodynamics', 'aircraft design', 'catia', 'ansys', 'cfd', 'structural analysis', 'flight mechanics', 'aviation'],
    'patterns': ['aeronautical engineer', 'aerospace engineer', 'aircraft engineer', 'aviation engineer'],
    'weight': 1.0
},
{
    'role': 'Chemical Engineer',
    'key_skills': ['process design', 'chemical processes', 'process simulation', 'aspen plus', 'hysys', 'process safety', 'plant design'],
    'patterns': ['chemical engineer', 'process engineer', 'chemical'],
    'weight': 1.0
},
{
    'role': 'Industrial Engineer',
    'key_skills': ['lean manufacturing', 'six sigma', 'process improvement', 'supply chain', 'operations management', 'quality control'],
    'patterns': ['industrial engineer', 'process improvement', 'operations engineer', 'lean engineer'],
    'weight': 1.0
},

# ============= HEALTHCARE & MEDICAL =============
{
    'role': 'Medical Doctor',
    'key_skills': ['clinical diagnosis', 'patient care', 'medical procedures', 'mbbs', 'md', 'treatment planning', 'emergency medicine'],
    'patterns': ['doctor', 'physician', 'medical officer', 'general practitioner', 'consultant'],
    'weight': 1.0
},
{
    'role': 'Nurse',
    'key_skills': ['patient care', 'nursing', 'medical procedures', 'medication administration', 'critical care', 'emergency response'],
    'patterns': ['nurse', 'registered nurse', 'staff nurse', 'nursing', 'rn'],
    'weight': 1.0
},
{
    'role': 'Pharmacist',
    'key_skills': ['pharmaceutical care', 'medication dispensing', 'drug interactions', 'pharmacy management', 'clinical pharmacy'],
    'patterns': ['pharmacist', 'pharmacy', 'clinical pharmacist'],
    'weight': 1.0
},

# ============= FINANCE & ACCOUNTING =============
{
    'role': 'Accountant',
    'key_skills': ['accounting', 'bookkeeping', 'financial reporting', 'taxation', 'tally', 'quickbooks', 'gst', 'auditing'],
    'patterns': ['accountant', 'accounts executive', 'finance executive', 'accounting'],
    'weight': 1.0
},
{
    'role': 'Financial Analyst',
    'key_skills': ['financial analysis', 'financial modeling', 'budgeting', 'forecasting', 'excel', 'valuation', 'investment analysis'],
    'patterns': ['financial analyst', 'finance analyst', 'investment analyst'],
    'weight': 1.0
},
{
    'role': 'Chartered Accountant',
    'key_skills': ['auditing', 'taxation', 'financial reporting', 'compliance', 'ifrs', 'ind as', 'direct tax', 'indirect tax'],
    'patterns': ['chartered accountant', 'ca', 'audit manager'],
    'weight': 1.0
},

# ============= MARKETING & SALES =============
{
    'role': 'Marketing Manager',
    'key_skills': ['marketing strategy', 'brand management', 'digital marketing', 'campaign management', 'market research', 'seo', 'social media'],
    'patterns': ['marketing manager', 'brand manager', 'marketing head'],
    'weight': 1.0
},
{
    'role': 'Digital Marketing Specialist',
    'key_skills': ['seo', 'sem', 'google ads', 'facebook ads', 'content marketing', 'social media marketing', 'email marketing', 'analytics'],
    'patterns': ['digital marketing', 'seo specialist', 'sem specialist', 'social media manager'],
    'weight': 1.0
},

# ============= HUMAN RESOURCES =============
{
    'role': 'HR Manager',
    'key_skills': ['recruitment', 'talent acquisition', 'employee relations', 'performance management', 'hr policies', 'compensation', 'training'],
    'patterns': ['hr manager', 'human resources manager', 'hr head', 'people manager'],
    'weight': 1.0
},
{
    'role': 'Recruiter',
    'key_skills': ['recruitment', 'talent acquisition', 'sourcing', 'screening', 'interviewing', 'candidate management', 'ats'],
    'patterns': ['recruiter', 'talent acquisition', 'recruitment specialist', 'hiring'],
    'weight': 1.0
},

# ============= EDUCATION & TRAINING =============
{
    'role': 'Teacher',
    'key_skills': ['teaching', 'curriculum development', 'classroom management', 'lesson planning', 'student assessment', 'education'],
    'patterns': ['teacher', 'educator', 'faculty', 'lecturer', 'professor'],
    'weight': 1.0
},
{
    'role': 'Corporate Trainer',
    'key_skills': ['training', 'facilitation', 'learning development', 'presentation skills', 'training design', 'instructional design'],
    'patterns': ['trainer', 'corporate trainer', 'training specialist', 'learning specialist'],
    'weight': 1.0
},

# ============= LEGAL =============
{
    'role': 'Lawyer',
    'key_skills': ['legal research', 'litigation', 'contract drafting', 'legal compliance', 'corporate law', 'legal advisory'],
    'patterns': ['lawyer', 'advocate', 'legal counsel', 'attorney', 'legal advisor'],
    'weight': 1.0
},

# ============= OPERATIONS & SUPPLY CHAIN =============
{
    'role': 'Supply Chain Manager',
    'key_skills': ['supply chain management', 'logistics', 'inventory management', 'procurement', 'vendor management', 'operations'],
    'patterns': ['supply chain manager', 'logistics manager', 'operations manager', 'procurement manager'],
    'weight': 1.0
},

# ============= CUSTOMER SERVICE =============
{
    'role': 'Customer Support Executive',
    'key_skills': ['customer service', 'communication', 'problem solving', 'crm', 'call handling', 'complaint resolution'],
    'patterns': ['customer support', 'customer service', 'support executive', 'customer care'],
    'weight': 1.0
},

# ============= ARCHITECTURE & DESIGN =============
{
    'role': 'Architect',
    'key_skills': ['architectural design', 'autocad', 'revit', 'sketchup', '3d modeling', 'building design', 'construction drawings'],
    'patterns': ['architect', 'architectural designer', 'design architect'],
    'weight': 1.0
},
{
    'role': 'Interior Designer',
    'key_skills': ['interior design', 'space planning', 'autocad', '3d max', 'sketchup', 'furniture design', 'color theory'],
    'patterns': ['interior designer', 'interior decorator', 'space designer'],
    'weight': 1.0
},

# ============= CONTENT & MEDIA =============
{
    'role': 'Content Writer',
    'key_skills': ['content writing', 'copywriting', 'seo writing', 'blogging', 'creative writing', 'editing', 'proofreading'],
    'patterns': ['content writer', 'copywriter', 'writer', 'content creator'],
    'weight': 1.0
},
{
    'role': 'Video Editor',
    'key_skills': ['video editing', 'adobe premiere', 'final cut pro', 'after effects', 'motion graphics', 'color grading'],
    'patterns': ['video editor', 'video producer', 'multimedia editor'],
    'weight': 1.0
},

{
    'role': 'Hotel Manager',
    'key_skills': ['hotel management', 'hospitality', 'guest relations', 'operations management', 'front office', 'food and beverage'],
    'patterns': ['hotel manager', 'hospitality manager', 'guest relations manager'],
    'weight': 1.0
},

{
    'role': 'Management Professional',
    'key_skills': ['management', 'leadership', 'strategy', 'operations', 'team management', 'planning'],
    'patterns': ['manager', 'management', 'supervisor', 'team lead'],
    'weight': 0.5
},
 {
        'role': 'Python Developer',
        'key_skills': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'sqlalchemy'],
        'patterns': ['python developer', 'python engineer', 'django developer', 'flask developer', 'fastapi developer'],
        'weight': 1.0
    },
    {
        'role': 'Java Developer',
        'key_skills': ['java', 'spring', 'spring boot', 'hibernate', 'jsp', 'maven', 'microservices'],
        'patterns': ['java developer', 'java engineer', 'spring developer', 'j2ee', 'spring boot developer'],
        'weight': 1.0
    },
    {
        'role': '.NET Developer',
        'key_skills': ['c#', '.net', 'asp.net', 'sql server', 'mvc', 'entity framework', '.net core'],
        'patterns': ['.net developer', 'dotnet developer', 'c# developer', 'asp.net developer', 'mvc developer'],
        'weight': 1.0
    },
    {
        'role': 'JavaScript Developer',
        'key_skills': ['javascript', 'react', 'angular', 'vue', 'node.js', 'express', 'typescript'],
        'patterns': ['javascript developer', 'js developer', 'frontend developer', 'react developer', 'angular developer'],
        'weight': 1.0
    },
    {
        'role': 'PHP Developer',
        'key_skills': ['php', 'laravel', 'codeigniter', 'symfony', 'mysql', 'wordpress', 'composer'],
        'patterns': ['php developer', 'laravel developer', 'codeigniter developer', 'wordpress developer'],
        'weight': 1.0
    },
    {
        'role': 'Ruby Developer',
        'key_skills': ['ruby', 'ruby on rails', 'rails', 'rspec', 'postgresql', 'sinatra'],
        'patterns': ['ruby developer', 'rails developer', 'ruby on rails developer'],
        'weight': 1.0
    },
    {
        'role': 'Go Developer',
        'key_skills': ['go', 'golang', 'gin', 'gorilla', 'postgresql', 'redis', 'microservices'],
        'patterns': ['go developer', 'golang developer', 'go engineer'],
        'weight': 1.0
    },
    {
        'role': 'C++ Developer',
        'key_skills': ['c++', 'stl', 'boost', 'qt', 'visual studio', 'object oriented programming'],
        'patterns': ['c++ developer', 'cpp developer', 'c++ engineer', 'c++ programmer'],
        'weight': 1.0
    },
    {
        'role': 'Rust Developer',
        'key_skills': ['rust', 'cargo', 'systems programming', 'memory safety', 'concurrency'],
        'patterns': ['rust developer', 'rust engineer', 'rust programmer'],
        'weight': 1.0
    },
    {
        'role': 'Scala Developer',
        'key_skills': ['scala', 'akka', 'play framework', 'spark', 'functional programming'],
        'patterns': ['scala developer', 'scala engineer', 'scala programmer'],
        'weight': 1.0
    },
    {
        'role': 'Kotlin Developer',
        'key_skills': ['kotlin', 'android', 'spring boot', 'coroutines', 'jetpack'],
        'patterns': ['kotlin developer', 'kotlin engineer', 'kotlin programmer'],
        'weight': 1.0
    },
    {
        'role': 'Swift Developer',
        'key_skills': ['swift', 'ios', 'xcode', 'cocoa touch', 'uikit', 'swiftui'],
        'patterns': ['swift developer', 'swift engineer', 'swift programmer'],
        'weight': 1.0
    },
    {
        'role': 'Full Stack Developer',
        'key_skills': ['javascript', 'react', 'node.js', 'python', 'django', 'postgresql', 'mongodb'],
        'patterns': ['full stack developer', 'fullstack developer', 'full-stack developer', 'full stack engineer'],
        'weight': 1.0
    },
    {
        'role': 'Frontend Developer',
        'key_skills': ['html', 'css', 'javascript', 'react', 'angular', 'vue', 'webpack', 'sass'],
        'patterns': ['frontend developer', 'front-end developer', 'ui developer', 'web developer'],
        'weight': 1.0
    },
    {
        'role': 'Backend Developer',
        'key_skills': ['api', 'database', 'microservices', 'rest', 'sql', 'nosql', 'redis'],
        'patterns': ['backend developer', 'back-end developer', 'api developer', 'server developer'],
        'weight': 1.0
    },
    {
        'role': 'MERN Stack Developer',
        'key_skills': ['mongodb', 'express', 'react', 'node.js', 'javascript', 'rest api'],
        'patterns': ['mern stack developer', 'mern developer', 'mern stack'],
        'weight': 1.0
    },
    {
        'role': 'MEAN Stack Developer',
        'key_skills': ['mongodb', 'express', 'angular', 'node.js', 'javascript', 'typescript'],
        'patterns': ['mean stack developer', 'mean developer', 'mean stack'],
        'weight': 1.0
    },
    {
        'role': 'Android Developer',
        'key_skills': ['android', 'java', 'kotlin', 'android studio', 'firebase', 'rest api'],
        'patterns': ['android developer', 'android engineer', 'mobile android developer'],
        'weight': 1.0
    },
    {
        'role': 'iOS Developer',
        'key_skills': ['ios', 'swift', 'objective-c', 'xcode', 'cocoa touch', 'core data'],
        'patterns': ['ios developer', 'ios engineer', 'iphone developer'],
        'weight': 1.0
    },
    {
        'role': 'Flutter Developer',
        'key_skills': ['flutter', 'dart', 'mobile development', 'cross-platform', 'firebase'],
        'patterns': ['flutter developer', 'flutter engineer', 'flutter mobile developer'],
        'weight': 1.0
    },
    {
        'role': 'React Native Developer',
        'key_skills': ['react native', 'javascript', 'mobile apps', 'ios', 'android', 'redux'],
        'patterns': ['react native developer', 'rn developer', 'react native engineer'],
        'weight': 1.0
    },
    {
        'role': 'Game Developer',
        'key_skills': ['unity', 'unreal engine', 'c++', 'c#', 'game design', '3d graphics'],
        'patterns': ['game developer', 'unity developer', 'unreal developer', 'game programmer'],
        'weight': 1.0
    },
    {
        'role': 'Embedded Systems Engineer',
        'key_skills': ['embedded c', 'firmware', 'microcontrollers', 'rtos', 'iot', 'arm'],
        'patterns': ['embedded engineer', 'embedded systems', 'firmware engineer', 'iot developer'],
        'weight': 1.0
    },
    {
        'role': 'Blockchain Developer',
        'key_skills': ['solidity', 'ethereum', 'smart contracts', 'web3', 'blockchain', 'cryptocurrency'],
        'patterns': ['blockchain developer', 'smart contract developer', 'web3 developer', 'crypto developer'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Data Scientist',
        'key_skills': ['python', 'machine learning', 'pandas', 'numpy', 'tensorflow', 'pytorch', 'statistics'],
        'patterns': ['data scientist', 'ml scientist', 'research scientist'],
        'weight': 1.0
    },
    {
        'role': 'Data Analyst',
        'key_skills': ['data analysis', 'excel', 'power bi', 'tableau', 'sql', 'python', 'statistics'],
        'patterns': ['data analyst', 'business intelligence analyst', 'analytics analyst'],
        'weight': 1.0
    },
    {
        'role': 'Data Engineer',
        'key_skills': ['python', 'spark', 'hadoop', 'kafka', 'airflow', 'etl', 'data pipelines'],
        'patterns': ['data engineer', 'big data engineer', 'data platform engineer'],
        'weight': 1.0
    },
    {
        'role': 'Machine Learning Engineer',
        'key_skills': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'python', 'mlops'],
        'patterns': ['machine learning engineer', 'ml engineer', 'ai engineer', 'deep learning engineer'],
        'weight': 1.0
    },
    {
        'role': 'Business Intelligence Analyst',
        'key_skills': ['power bi', 'tableau', 'sql', 'data visualization', 'reporting', 'dax'],
        'patterns': ['business intelligence', 'bi analyst', 'bi developer', 'reporting analyst'],
        'weight': 1.0
    },
    {
        'role': 'ETL Developer',
        'key_skills': ['etl', 'informatica', 'ssis', 'data warehousing', 'sql', 'talend'],
        'patterns': ['etl developer', 'data warehouse developer', 'informatica developer'],
        'weight': 1.0
    },
    {
        'role': 'Tableau Developer',
        'key_skills': ['tableau', 'data visualization', 'sql', 'dashboard design', 'analytics'],
        'patterns': ['tableau developer', 'tableau consultant', 'tableau specialist'],
        'weight': 1.0
    },
    {
        'role': 'Power BI Developer',
        'key_skills': ['power bi', 'dax', 'power query', 'data modeling', 'sql', 'excel'],
        'patterns': ['power bi developer', 'powerbi developer', 'power bi consultant'],
        'weight': 1.0
    },
    
    
    {
        'role': 'DevOps Engineer',
        'key_skills': ['docker', 'kubernetes', 'jenkins', 'terraform', 'aws', 'azure', 'ci/cd'],
        'patterns': ['devops engineer', 'devops', 'infrastructure engineer', 'sre'],
        'weight': 1.0
    },
    {
        'role': 'Cloud Engineer',
        'key_skills': ['aws', 'azure', 'gcp', 'terraform', 'cloudformation', 'cloud architecture'],
        'patterns': ['cloud engineer', 'aws engineer', 'azure engineer', 'cloud architect'],
        'weight': 1.0
    },
    {
        'role': 'AWS Solutions Architect',
        'key_skills': ['aws', 'ec2', 's3', 'lambda', 'cloudformation', 'vpc', 'iam'],
        'patterns': ['aws solutions architect', 'aws architect', 'cloud solutions architect'],
        'weight': 1.0
    },
    {
        'role': 'Azure Cloud Engineer',
        'key_skills': ['azure', 'azure devops', 'arm templates', 'azure functions', 'active directory'],
        'patterns': ['azure engineer', 'azure cloud engineer', 'azure developer'],
        'weight': 1.0
    },
    {
        'role': 'Site Reliability Engineer',
        'key_skills': ['sre', 'monitoring', 'prometheus', 'grafana', 'kubernetes', 'incident management'],
        'patterns': ['site reliability engineer', 'sre', 'reliability engineer'],
        'weight': 1.0
    },
    {
        'role': 'Kubernetes Engineer',
        'key_skills': ['kubernetes', 'docker', 'helm', 'container orchestration', 'microservices'],
        'patterns': ['kubernetes engineer', 'k8s engineer', 'container engineer'],
        'weight': 1.0
    },
    {
        'role': 'System Administrator',
        'key_skills': ['linux', 'windows server', 'networking', 'bash', 'powershell', 'active directory'],
        'patterns': ['system administrator', 'sysadmin', 'systems admin', 'infrastructure admin'],
        'weight': 1.0
    },
    {
        'role': 'Network Engineer',
        'key_skills': ['networking', 'cisco', 'routing', 'switching', 'firewalls', 'tcp/ip'],
        'patterns': ['network engineer', 'network administrator', 'network specialist'],
        'weight': 1.0
    },
    
    {
        'role': 'Cybersecurity Engineer',
        'key_skills': ['security', 'penetration testing', 'vulnerability assessment', 'firewalls', 'siem'],
        'patterns': ['cybersecurity engineer', 'security engineer', 'infosec engineer'],
        'weight': 1.0
    },
    {
        'role': 'Penetration Tester',
        'key_skills': ['penetration testing', 'ethical hacking', 'vulnerability assessment', 'metasploit', 'burp suite'],
        'patterns': ['penetration tester', 'pen tester', 'ethical hacker', 'security tester'],
        'weight': 1.0
    },
    {
        'role': 'Security Analyst',
        'key_skills': ['security monitoring', 'threat analysis', 'siem', 'incident response', 'log analysis'],
        'patterns': ['security analyst', 'cybersecurity analyst', 'infosec analyst'],
        'weight': 1.0
    },
    {
        'role': 'Information Security Manager',
        'key_skills': ['information security', 'risk management', 'compliance', 'iso 27001', 'security policies'],
        'patterns': ['information security manager', 'infosec manager', 'security manager'],
        'weight': 1.0
    },
    
    {
        'role': 'QA Engineer',
        'key_skills': ['testing', 'automation', 'selenium', 'junit', 'testng', 'api testing'],
        'patterns': ['qa engineer', 'quality assurance engineer', 'test engineer'],
        'weight': 1.0
    },
    {
        'role': 'Automation Test Engineer',
        'key_skills': ['selenium', 'cypress', 'playwright', 'automation testing', 'java', 'python'],
        'patterns': ['automation engineer', 'test automation engineer', 'sdet'],
        'weight': 1.0
    },
    {
        'role': 'Manual Tester',
        'key_skills': ['manual testing', 'test cases', 'bug tracking', 'jira', 'regression testing'],
        'patterns': ['manual tester', 'manual test engineer', 'qa tester'],
        'weight': 1.0
    },
    {
        'role': 'Performance Test Engineer',
        'key_skills': ['performance testing', 'jmeter', 'loadrunner', 'load testing', 'stress testing'],
        'patterns': ['performance test engineer', 'performance tester', 'load test engineer'],
        'weight': 1.0
    },
    {
        'role': 'Quality Analyst',
        'key_skills': ['quality analysis', 'manual testing', 'test cases', 'bug tracking', 'regression testing'],
        'patterns': ['quality analyst', 'qa analyst', 'software tester'],
        'weight': 1.0
    },
    

    
    {
        'role': 'Database Administrator',
        'key_skills': ['sql', 'oracle', 'mysql', 'postgresql', 'database administration', 'backup recovery'],
        'patterns': ['database administrator', 'dba', 'sql dba', 'oracle dba'],
        'weight': 1.0
    },
    {
        'role': 'Database Developer',
        'key_skills': ['sql', 'stored procedures', 'database design', 'query optimization', 'indexing'],
        'patterns': ['database developer', 'sql developer', 'database programmer'],
        'weight': 1.0
    },
    {
        'role': 'Software Architect',
        'key_skills': ['software architecture', 'system design', 'microservices', 'design patterns', 'scalability'],
        'patterns': ['software architect', 'solution architect', 'technical architect'],
        'weight': 1.0
    },
    {
        'role': 'Solutions Architect',
        'key_skills': ['solution architecture', 'system design', 'cloud architecture', 'technical leadership'],
        'patterns': ['solutions architect', 'solution architect', 'enterprise architect'],
        'weight': 1.0
    },
    {
        'role': 'Product Architect',
        'key_skills': ['product architecture', 'system design', 'technical strategy', 'product development'],
        'patterns': ['product architect', 'technical product architect'],
        'weight': 1.0
    },
    
    
    {
        'role': 'UI/UX Designer',
        'key_skills': ['ui design', 'ux design', 'figma', 'adobe xd', 'prototyping', 'user research'],
        'patterns': ['ui/ux designer', 'ui designer', 'ux designer', 'product designer'],
        'weight': 1.0
    },
    {
        'role': 'Graphic Designer',
        'key_skills': ['graphic design', 'photoshop', 'illustrator', 'indesign', 'branding', 'visual design'],
        'patterns': ['graphic designer', 'visual designer', 'creative designer'],
        'weight': 1.0
    },
    {
        'role': 'Web Designer',
        'key_skills': ['web design', 'html', 'css', 'figma', 'responsive design', 'adobe xd'],
        'patterns': ['web designer', 'website designer', 'ui web designer'],
        'weight': 1.0
    },
    {
        'role': 'Motion Graphics Designer',
        'key_skills': ['after effects', 'motion graphics', 'animation', 'video editing', 'adobe premiere'],
        'patterns': ['motion graphics designer', 'motion designer', 'animator'],
        'weight': 1.0
    },

    
    {
        'role': 'Mechanical Engineer',
        'key_skills': ['autocad', 'solidworks', 'catia', 'mechanical design', 'manufacturing', 'cad'],
        'patterns': ['mechanical engineer', 'design engineer', 'cad engineer', 'product design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Mechanical Design Engineer',
        'key_skills': ['solidworks', 'catia', 'creo', 'cad', 'mechanical design', '3d modeling'],
        'patterns': ['mechanical design engineer', 'design engineer mechanical', 'cad design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Manufacturing Engineer',
        'key_skills': ['manufacturing processes', 'production planning', 'quality control', 'lean manufacturing'],
        'patterns': ['manufacturing engineer', 'production engineer', 'process engineer manufacturing'],
        'weight': 1.0
    },
    {
        'role': 'Production Engineer',
        'key_skills': ['production planning', 'quality control', 'process optimization', 'manufacturing'],
        'patterns': ['production engineer', 'production manager', 'production supervisor'],
        'weight': 1.0
    },
    {
        'role': 'Maintenance Engineer',
        'key_skills': ['preventive maintenance', 'troubleshooting', 'equipment maintenance', 'reliability'],
        'patterns': ['maintenance engineer', 'plant maintenance engineer', 'facilities engineer'],
        'weight': 1.0
    },
    {
        'role': 'Quality Engineer',
        'key_skills': ['quality control', 'quality assurance', 'six sigma', 'statistical analysis', 'iso'],
        'patterns': ['quality engineer', 'quality control engineer', 'qa engineer manufacturing'],
        'weight': 1.0
    },
    {
        'role': 'Automobile Engineer',
        'key_skills': ['automotive engineering', 'vehicle design', 'catia', 'automotive systems'],
        'patterns': ['automobile engineer', 'automotive engineer', 'vehicle engineer'],
        'weight': 1.0
    },
    

    
    {
        'role': 'Civil Engineer',
        'key_skills': ['autocad', 'civil 3d', 'structural design', 'construction', 'surveying', 'revit'],
        'patterns': ['civil engineer', 'structural engineer', 'construction engineer', 'site engineer'],
        'weight': 1.0
    },
    {
        'role': 'Structural Engineer',
        'key_skills': ['structural analysis', 'staad pro', 'etabs', 'structural design', 'rcc design'],
        'patterns': ['structural engineer', 'structural design engineer', 'structure engineer'],
        'weight': 1.0
    },
    {
        'role': 'Construction Engineer',
        'key_skills': ['construction management', 'site supervision', 'project planning', 'quantity surveying'],
        'patterns': ['construction engineer', 'site engineer', 'construction manager'],
        'weight': 1.0
    },
    {
        'role': 'Quantity Surveyor',
        'key_skills': ['quantity surveying', 'cost estimation', 'bill of quantities', 'contract management'],
        'patterns': ['quantity surveyor', 'qs engineer', 'estimator'],
        'weight': 1.0
    },
    {
        'role': 'Highway Engineer',
        'key_skills': ['highway design', 'transportation engineering', 'pavement design', 'traffic engineering'],
        'patterns': ['highway engineer', 'transportation engineer', 'traffic engineer'],
        'weight': 1.0
    },
    {
        'role': 'Geotechnical Engineer',
        'key_skills': ['soil mechanics', 'foundation design', 'geotechnical investigation', 'soil testing'],
        'patterns': ['geotechnical engineer', 'soil engineer', 'foundation engineer'],
        'weight': 1.0
    },
    

    
    {
        'role': 'Electrical Engineer',
        'key_skills': ['electrical design', 'power systems', 'plc', 'scada', 'autocad electrical'],
        'patterns': ['electrical engineer', 'power engineer', 'electrical design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Electronics Engineer',
        'key_skills': ['circuit design', 'pcb design', 'embedded systems', 'microcontrollers', 'vlsi'],
        'patterns': ['electronics engineer', 'electronics design engineer', 'circuit design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Instrumentation Engineer',
        'key_skills': ['instrumentation', 'control systems', 'plc', 'dcs', 'scada', 'calibration'],
        'patterns': ['instrumentation engineer', 'control engineer', 'i&c engineer'],
        'weight': 1.0
    },
    {
        'role': 'Power Electronics Engineer',
        'key_skills': ['power electronics', 'inverters', 'converters', 'motor drives', 'power supply design'],
        'patterns': ['power electronics engineer', 'power systems engineer'],
        'weight': 1.0
    },
    {
        'role': 'VLSI Design Engineer',
        'key_skills': ['vlsi', 'verilog', 'vhdl', 'rtl design', 'asic design', 'fpga'],
        'patterns': ['vlsi engineer', 'vlsi design engineer', 'asic design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Telecommunications Engineer',
        'key_skills': ['telecommunications', 'networking', 'rf engineering', 'wireless communication'],
        'patterns': ['telecommunications engineer', 'telecom engineer', 'rf engineer'],
        'weight': 1.0
    },

    
    {
        'role': 'Chemical Engineer',
        'key_skills': ['chemical processes', 'process design', 'aspen plus', 'process simulation', 'plant design'],
        'patterns': ['chemical engineer', 'process engineer', 'process design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Process Engineer',
        'key_skills': ['process optimization', 'process design', 'chemical engineering', 'plant operations'],
        'patterns': ['process engineer', 'process development engineer', 'chemical process engineer'],
        'weight': 1.0
    },
    {
        'role': 'Petroleum Engineer',
        'key_skills': ['petroleum engineering', 'reservoir engineering', 'drilling', 'production engineering'],
        'patterns': ['petroleum engineer', 'reservoir engineer', 'drilling engineer'],
        'weight': 1.0
    },
    {
        'role': 'Refinery Engineer',
        'key_skills': ['refinery operations', 'process engineering', 'distillation', 'chemical processing'],
        'patterns': ['refinery engineer', 'refinery operations engineer'],
        'weight': 1.0
    },

    
    {
        'role': 'Aeronautical Engineer',
        'key_skills': ['aerodynamics', 'aircraft design', 'catia', 'ansys', 'cfd', 'flight mechanics'],
        'patterns': ['aeronautical engineer', 'aerospace engineer', 'aircraft engineer'],
        'weight': 1.0
    },
    {
        'role': 'Aerospace Design Engineer',
        'key_skills': ['aerospace design', 'catia', 'cfd', 'structural analysis', 'aircraft systems'],
        'patterns': ['aerospace design engineer', 'aircraft design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Flight Test Engineer',
        'key_skills': ['flight testing', 'test engineering', 'data analysis', 'aviation'],
        'patterns': ['flight test engineer', 'test pilot engineer'],
        'weight': 1.0
    },

    
    {
        'role': 'Industrial Engineer',
        'key_skills': ['lean manufacturing', 'six sigma', 'process improvement', 'operations management'],
        'patterns': ['industrial engineer', 'process improvement engineer', 'operations engineer'],
        'weight': 1.0
    },
    {
        'role': 'Lean Six Sigma Consultant',
        'key_skills': ['lean manufacturing', 'six sigma', 'process optimization', 'continuous improvement'],
        'patterns': ['lean six sigma', 'six sigma consultant', 'lean consultant'],
        'weight': 1.0
    },
    {
        'role': 'Plant Engineer',
        'key_skills': ['plant operations', 'maintenance management', 'process optimization', 'safety management'],
        'patterns': ['plant engineer', 'plant manager', 'facility engineer'],
        'weight': 1.0
    },
    {
        'role': 'Metallurgical Engineer',
        'key_skills': ['metallurgy', 'materials science', 'heat treatment', 'welding', 'material testing'],
        'patterns': ['metallurgical engineer', 'metallurgy engineer', 'materials engineer'],
        'weight': 1.0
    },
    

    
    {
        'role': 'Biomedical Engineer',
        'key_skills': ['biomedical engineering', 'medical devices', 'biomechanics', 'signal processing'],
        'patterns': ['biomedical engineer', 'medical device engineer', 'clinical engineer'],
        'weight': 1.0
    },
    {
        'role': 'Environmental Engineer',
        'key_skills': ['environmental engineering', 'waste management', 'water treatment', 'pollution control'],
        'patterns': ['environmental engineer', 'environmental consultant', 'sustainability engineer'],
        'weight': 1.0
    },
    {
        'role': 'Safety Engineer',
        'key_skills': ['safety management', 'osha', 'risk assessment', 'industrial safety', 'hse'],
        'patterns': ['safety engineer', 'hse engineer', 'safety officer'],
        'weight': 1.0
    },
    

    
    {
        'role': 'Medical Doctor',
        'key_skills': ['clinical diagnosis', 'patient care', 'medical procedures', 'mbbs', 'treatment planning'],
        'patterns': ['doctor', 'physician', 'medical officer', 'general practitioner', 'consultant doctor'],
        'weight': 1.0
    },
    {
        'role': 'Surgeon',
        'key_skills': ['surgery', 'surgical procedures', 'patient care', 'operating room', 'medical procedures'],
        'patterns': ['surgeon', 'surgical consultant', 'operating surgeon'],
        'weight': 1.0
    },
    {
        'role': 'Dentist',
        'key_skills': ['dental procedures', 'oral surgery', 'teeth cleaning', 'dental care', 'orthodontics'],
        'patterns': ['dentist', 'dental surgeon', 'orthodontist'],
        'weight': 1.0
    },
    {
        'role': 'Nurse',
        'key_skills': ['patient care', 'nursing', 'medication administration', 'critical care', 'emergency response'],
        'patterns': ['nurse', 'registered nurse', 'staff nurse', 'nursing officer', 'rn'],
        'weight': 1.0
    },
    {
        'role': 'Pharmacist',
        'key_skills': ['pharmaceutical care', 'medication dispensing', 'drug interactions', 'pharmacy management'],
        'patterns': ['pharmacist', 'clinical pharmacist', 'hospital pharmacist'],
        'weight': 1.0
    },

    {
        'role': 'Aircraft Maintenance Engineer (AME)',
        'key_skills': ['aircraft maintenance', 'dgca', 'ame license', 'aircraft systems', 'troubleshooting', 'airframe', 'powerplant', 'avionics'],
        'patterns': ['aircraft maintenance engineer', 'ame', 'aircraft engineer', 'aviation maintenance', 'aircraft mechanic'],
        'weight': 1.0
    },
    {
        'role': 'Aeronautical Engineer',
        'key_skills': ['aerodynamics', 'aircraft design', 'catia', 'ansys', 'cfd', 'flight mechanics', 'structural analysis', 'aviation'],
        'patterns': ['aeronautical engineer', 'aerospace engineer', 'aircraft engineer', 'aviation engineer', 'flight engineer'],
        'weight': 1.0
    },
    {
        'role': 'Aerospace Design Engineer',
        'key_skills': ['aerospace design', 'catia', 'solidworks', 'cfd analysis', 'structural analysis', 'aircraft systems', 'ansys'],
        'patterns': ['aerospace design engineer', 'aircraft design engineer', 'aeronautical design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Avionics Engineer',
        'key_skills': ['avionics systems', 'aircraft electronics', 'navigation systems', 'communication systems', 'radar', 'flight instruments'],
        'patterns': ['avionics engineer', 'avionics technician', 'aircraft electronics engineer'],
        'weight': 1.0
    },
    {
        'role': 'Flight Test Engineer',
        'key_skills': ['flight testing', 'test engineering', 'data analysis', 'aviation', 'aircraft performance', 'instrumentation'],
        'patterns': ['flight test engineer', 'test pilot engineer', 'flight operations engineer'],
        'weight': 1.0
    },
    {
        'role': 'Aircraft Structural Engineer',
        'key_skills': ['structural analysis', 'stress analysis', 'fatigue analysis', 'composite materials', 'fea', 'catia'],
        'patterns': ['aircraft structural engineer', 'structures engineer', 'airframe engineer'],
        'weight': 1.0
    },
    {
        'role': 'Propulsion Engineer',
        'key_skills': ['jet engines', 'turbine engines', 'engine performance', 'propulsion systems', 'thermodynamics'],
        'patterns': ['propulsion engineer', 'engine engineer', 'powerplant engineer'],
        'weight': 1.0
    },
    {
        'role': 'Commercial Pilot',
        'key_skills': ['flight operations', 'cpl license', 'atpl', 'aircraft operation', 'navigation', 'flight safety', 'aviation regulations'],
        'patterns': ['commercial pilot', 'airline pilot', 'cpl', 'captain', 'first officer', 'co-pilot'],
        'weight': 1.0
    },
    {
        'role': 'Private Pilot',
        'key_skills': ['ppl license', 'flight operations', 'aircraft operation', 'navigation', 'flight planning'],
        'patterns': ['private pilot', 'ppl', 'pilot trainee'],
        'weight': 1.0
    },
    {
        'role': 'Helicopter Pilot',
        'key_skills': ['helicopter operations', 'rotary wing', 'flight operations', 'aviation', 'helicopter flying'],
        'patterns': ['helicopter pilot', 'chopper pilot', 'rotary wing pilot'],
        'weight': 1.0
    },
    {
        'role': 'Flight Instructor',
        'key_skills': ['flight training', 'aviation training', 'cfi', 'aircraft operation', 'flight instruction'],
        'patterns': ['flight instructor', 'flying instructor', 'cfi', 'aviation instructor'],
        'weight': 1.0
    },
    {
        'role': 'Air Traffic Controller',
        'key_skills': ['air traffic control', 'atc', 'radar operations', 'aviation safety', 'communication', 'flight coordination'],
        'patterns': ['air traffic controller', 'atc', 'air traffic control officer'],
        'weight': 1.0
    },
    {
        'role': 'Flight Dispatcher',
        'key_skills': ['flight planning', 'weather analysis', 'route planning', 'fuel calculation', 'aviation regulations'],
        'patterns': ['flight dispatcher', 'flight operations officer', 'dispatcher'],
        'weight': 1.0
    },
    {
        'role': 'Cabin Crew / Flight Attendant',
        'key_skills': ['customer service', 'safety procedures', 'emergency response', 'hospitality', 'passenger care', 'in-flight service'],
        'patterns': ['cabin crew', 'flight attendant', 'air hostess', 'airhostess', 'steward', 'stewardess', 'flight steward'],
        'weight': 1.0
    },
    {
        'role': 'Ground Staff',
        'key_skills': ['airport operations', 'passenger handling', 'check-in', 'baggage handling', 'customer service'],
        'patterns': ['ground staff', 'ground handling', 'airport staff', 'airport operations'],
        'weight': 1.0
    },
    {
        'role': 'Airport Operations Manager',
        'key_skills': ['airport management', 'operations management', 'aviation', 'safety management', 'coordination'],
        'patterns': ['airport operations manager', 'airport manager', 'aviation operations manager'],
        'weight': 1.0
    },
    {
        'role': 'Aviation Safety Officer',
        'key_skills': ['aviation safety', 'safety management', 'accident investigation', 'risk assessment', 'compliance'],
        'patterns': ['aviation safety officer', 'flight safety officer', 'safety manager aviation'],
        'weight': 1.0
    },
    {
        'role': 'Drone Pilot / UAV Operator',
        'key_skills': ['drone operation', 'uav', 'remote pilot', 'aerial photography', 'dgca rpas'],
        'patterns': ['drone pilot', 'uav operator', 'drone operator', 'rpas pilot', 'unmanned aircraft pilot'],
        'weight': 1.0
    },

    
    {
        'role': 'Locomotive Pilot / Train Driver',
        'key_skills': ['train operation', 'locomotive driving', 'railway safety', 'signaling', 'railway operations'],
        'patterns': ['locomotive pilot', 'loco pilot', 'train driver', 'engine driver', 'motorman', 'train operator'],
        'weight': 1.0
    },
    {
        'role': 'Assistant Loco Pilot',
        'key_skills': ['train assistance', 'locomotive operations', 'railway safety', 'signaling'],
        'patterns': ['assistant loco pilot', 'alp', 'assistant train driver', 'assistant locomotive pilot'],
        'weight': 1.0
    },
    {
        'role': 'Railway Engineer',
        'key_skills': ['railway engineering', 'track maintenance', 'signaling', 'railway infrastructure'],
        'patterns': ['railway engineer', 'permanent way engineer', 'track engineer'],
        'weight': 1.0
    },
    {
        'role': 'Signal & Telecom Engineer',
        'key_skills': ['railway signaling', 'telecommunications', 'interlocking', 'signal maintenance'],
        'patterns': ['signal engineer', 'telecom engineer railway', 's&t engineer', 'signaling engineer'],
        'weight': 1.0
    },
    {
        'role': 'Railway Technician',
        'key_skills': ['railway maintenance', 'electrical systems', 'mechanical systems', 'troubleshooting'],
        'patterns': ['railway technician', 'train technician', 'railway mechanic'],
        'weight': 1.0
    },
    {
        'role': 'Train Conductor / Guard',
        'key_skills': ['train operations', 'passenger safety', 'ticketing', 'railway operations'],
        'patterns': ['train conductor', 'train guard', 'railway guard', 'ticket collector'],
        'weight': 1.0
    },
    {
        'role': 'Station Master',
        'key_skills': ['station management', 'railway operations', 'passenger coordination', 'train scheduling'],
        'patterns': ['station master', 'station manager', 'railway station master'],
        'weight': 1.0
    },
    {
        'role': 'Metro Train Operator',
        'key_skills': ['metro operations', 'train driving', 'urban transport', 'safety protocols'],
        'patterns': ['metro train operator', 'metro driver', 'subway operator'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Civil Engineer',
        'key_skills': ['autocad', 'civil 3d', 'structural design', 'construction', 'surveying', 'revit', 'site planning'],
        'patterns': ['civil engineer', 'structural engineer', 'construction engineer', 'site engineer', 'civil engineering'],
        'weight': 1.0
    },
    {
        'role': 'Structural Engineer',
        'key_skills': ['structural analysis', 'staad pro', 'etabs', 'structural design', 'rcc design', 'steel structures'],
        'patterns': ['structural engineer', 'structural design engineer', 'structure engineer'],
        'weight': 1.0
    },
    {
        'role': 'Construction Manager',
        'key_skills': ['construction management', 'project management', 'site supervision', 'planning', 'scheduling'],
        'patterns': ['construction manager', 'project manager construction', 'site manager'],
        'weight': 1.0
    },
    {
        'role': 'Site Engineer',
        'key_skills': ['site supervision', 'construction', 'quality control', 'safety management', 'civil work'],
        'patterns': ['site engineer', 'site supervisor', 'civil site engineer'],
        'weight': 1.0
    },
    {
        'role': 'Quantity Surveyor',
        'key_skills': ['quantity surveying', 'cost estimation', 'bill of quantities', 'tendering', 'contract management'],
        'patterns': ['quantity surveyor', 'qs', 'estimator', 'cost estimator'],
        'weight': 1.0
    },
    {
        'role': 'Highway Engineer',
        'key_skills': ['highway design', 'transportation engineering', 'pavement design', 'traffic engineering', 'road construction'],
        'patterns': ['highway engineer', 'road engineer', 'transportation engineer', 'traffic engineer'],
        'weight': 1.0
    },
    {
        'role': 'Geotechnical Engineer',
        'key_skills': ['soil mechanics', 'foundation design', 'geotechnical investigation', 'soil testing', 'ground improvement'],
        'patterns': ['geotechnical engineer', 'soil engineer', 'foundation engineer', 'geo engineer'],
        'weight': 1.0
    },
    {
        'role': 'Water Resources Engineer',
        'key_skills': ['hydrology', 'water resources', 'irrigation', 'drainage', 'hydraulic design'],
        'patterns': ['water resources engineer', 'irrigation engineer', 'hydraulic engineer'],
        'weight': 1.0
    },
    {
        'role': 'Bridge Engineer',
        'key_skills': ['bridge design', 'structural analysis', 'bridge construction', 'staad pro'],
        'patterns': ['bridge engineer', 'bridge design engineer', 'bridge construction engineer'],
        'weight': 1.0
    },
    {
        'role': 'Urban Planner',
        'key_skills': ['urban planning', 'land use planning', 'gis', 'city planning', 'development planning'],
        'patterns': ['urban planner', 'town planner', 'city planner'],
        'weight': 1.0
    },
    
    {
        'role': 'Mechanical Engineer',
        'key_skills': ['autocad', 'solidworks', 'catia', 'mechanical design', 'manufacturing', 'cad', 'thermodynamics'],
        'patterns': ['mechanical engineer', 'design engineer', 'mechanical design engineer', 'product design engineer'],
        'weight': 1.0
    },
    {
        'role': 'Mechanical Design Engineer',
        'key_skills': ['solidworks', 'catia', 'creo', 'cad', '3d modeling', 'mechanical design', 'product development'],
        'patterns': ['mechanical design engineer', 'design engineer mechanical', 'cad design engineer'],
        'weight': 1.0
    },

    {
        'role': 'Manufacturing Engineer',
        'key_skills': ['manufacturing processes', 'production planning', 'quality control', 'lean manufacturing', 'process optimization'],
        'patterns': ['manufacturing engineer', 'production engineer', 'process engineer manufacturing'],
        'weight': 1.0
    },
    {
        'role': 'Production Engineer',
        'key_skills': ['production planning', 'quality control', 'manufacturing', 'operations', 'process improvement'],
        'patterns': ['production engineer', 'production manager', 'production supervisor'],
        'weight': 1.0
    },
    {
        'role': 'Maintenance Engineer',
        'key_skills': ['preventive maintenance', 'troubleshooting', 'equipment maintenance', 'reliability', 'tpm'],
        'patterns': ['maintenance engineer', 'plant maintenance engineer', 'maintenance manager'],
        'weight': 1.0
    },
    {
        'role': 'Quality Engineer',
        'key_skills': ['quality control', 'quality assurance', 'six sigma', 'iso', 'inspection', 'testing'],
        'patterns': ['quality engineer', 'quality control engineer', 'qa engineer manufacturing'],
        'weight': 1.0
    },
    {
        'role': 'Automobile Engineer',
        'key_skills': ['automotive engineering', 'vehicle design', 'catia', 'automotive systems', 'engine design'],
        'patterns': ['automobile engineer', 'automotive engineer', 'vehicle engineer'],
        'weight': 1.0
    },
    {
        'role': 'HVAC Engineer',
        'key_skills': ['hvac', 'air conditioning', 'ventilation', 'refrigeration', 'thermal systems'],
        'patterns': ['hvac engineer', 'hvac design engineer', 'mechanical hvac'],
        'weight': 1.0
    },
    {
        'role': 'Tool & Die Maker',
        'key_skills': ['tool design', 'die making', 'cnc programming', 'machining', 'precision engineering'],
        'patterns': ['tool and die maker', 'tool designer', 'die designer'],
        'weight': 1.0
    },
    {
        'role': 'CNC Programmer',
        'key_skills': ['cnc programming', 'machining', 'g-code', 'cnc operation', 'manufacturing'],
        'patterns': ['cnc programmer', 'cnc operator', 'cnc machinist'],
        'weight': 1.0
    },
    {
        'role': 'Welding Engineer',
        'key_skills': ['welding', 'welding inspection', 'welding codes', 'ndt', 'fabrication'],
        'patterns': ['welding engineer', 'welding inspector', 'welding supervisor'],
        'weight': 1.0
    },
    {
        'role': 'Marine Engineer',
        'key_skills': ['marine engineering', 'ship systems', 'marine machinery', 'propulsion systems'],
        'patterns': ['marine engineer', 'ship engineer', 'naval architect'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Hotel Manager',
        'key_skills': ['hotel management', 'hospitality', 'guest relations', 'operations management', 'front office'],
        'patterns': ['hotel manager', 'hospitality manager', 'general manager hotel', 'hotel operations manager'],
        'weight': 1.0
    },
    {
        'role': 'Front Office Manager',
        'key_skills': ['front office operations', 'guest services', 'hotel management', 'reception', 'booking'],
        'patterns': ['front office manager', 'fom', 'reception manager'],
        'weight': 1.0
    },
    {
        'role': 'Housekeeping Manager',
        'key_skills': ['housekeeping', 'hotel operations', 'staff management', 'cleanliness standards'],
        'patterns': ['housekeeping manager', 'housekeeping supervisor', 'executive housekeeper'],
        'weight': 1.0
    },
    {
        'role': 'Food & Beverage Manager',
        'key_skills': ['food and beverage', 'restaurant management', 'menu planning', 'hospitality', 'service'],
        'patterns': ['food and beverage manager', 'f&b manager', 'restaurant manager'],
        'weight': 1.0
    },
    {
        'role': 'Chef / Cook',
        'key_skills': ['cooking', 'culinary', 'food preparation', 'menu planning', 'kitchen management'],
        'patterns': ['chef', 'executive chef', 'head chef', 'cook', 'sous chef', 'pastry chef'],
        'weight': 1.0
    },
    {
        'role': 'Bartender',
        'key_skills': ['bartending', 'mixology', 'beverage service', 'customer service', 'cocktails'],
        'patterns': ['bartender', 'mixologist', 'bar manager'],
        'weight': 1.0
    },
    {
        'role': 'Travel Consultant',
        'key_skills': ['travel planning', 'tour packages', 'itinerary planning', 'customer service', 'ticketing'],
        'patterns': ['travel consultant', 'travel agent', 'tour consultant', 'travel advisor'],
        'weight': 1.0
    },
    {
        'role': 'Tour Guide',
        'key_skills': ['tour guiding', 'tourism', 'customer service', 'local knowledge', 'languages'],
        'patterns': ['tour guide', 'tourist guide', 'travel guide'],
        'weight': 1.0
    },
    {
        'role': 'Event Manager',
        'key_skills': ['event planning', 'event management', 'coordination', 'logistics', 'vendor management'],
        'patterns': ['event manager', 'event planner', 'event coordinator'],
        'weight': 1.0
    },
    {
        'role': 'Cruise Ship Staff',
        'key_skills': ['hospitality', 'customer service', 'cruise operations', 'entertainment', 'guest services'],
        'patterns': ['cruise ship staff', 'cruise director', 'cruise attendant'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Store Manager',
        'key_skills': ['retail management', 'inventory management', 'sales', 'customer service', 'staff management'],
        'patterns': ['store manager', 'retail manager', 'shop manager'],
        'weight': 1.0
    },
    {
        'role': 'Sales Associate',
        'key_skills': ['customer service', 'sales', 'product knowledge', 'retail', 'cash handling'],
        'patterns': ['sales associate', 'retail associate', 'sales representative retail'],
        'weight': 1.0
    },
    {
        'role': 'E-commerce Manager',
        'key_skills': ['e-commerce', 'online retail', 'digital marketing', 'inventory management', 'analytics'],
        'patterns': ['e-commerce manager', 'ecommerce manager', 'online retail manager'],
        'weight': 1.0
    },
    {
        'role': 'Merchandiser',
        'key_skills': ['merchandising', 'product placement', 'inventory', 'visual merchandising', 'retail'],
        'patterns': ['merchandiser', 'visual merchandiser', 'retail merchandiser'],
        'weight': 1.0
    },
    {
        'role': 'Category Manager',
        'key_skills': ['category management', 'product assortment', 'pricing', 'vendor management', 'analytics'],
        'patterns': ['category manager', 'product category manager'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Agricultural Engineer',
        'key_skills': ['agricultural engineering', 'farm machinery', 'irrigation', 'soil science', 'crop production'],
        'patterns': ['agricultural engineer', 'farm engineer', 'agri engineer'],
        'weight': 1.0
    },
    {
        'role': 'Agronomist',
        'key_skills': ['agronomy', 'crop science', 'soil management', 'pest control', 'farming'],
        'patterns': ['agronomist', 'crop consultant', 'agricultural scientist'],
        'weight': 1.0
    },
    {
        'role': 'Horticulturist',
        'key_skills': ['horticulture', 'plant science', 'gardening', 'landscaping', 'crop cultivation'],
        'patterns': ['horticulturist', 'horticulture specialist', 'garden specialist'],
        'weight': 1.0
    },
    {
        'role': 'Agricultural Officer',
        'key_skills': ['agriculture', 'farm management', 'crop planning', 'extension services', 'rural development'],
        'patterns': ['agricultural officer', 'agriculture officer', 'farm officer'],
        'weight': 1.0
    },
    {
        'role': 'Veterinarian',
        'key_skills': ['veterinary medicine', 'animal care', 'surgery', 'diagnosis', 'animal health'],
        'patterns': ['veterinarian', 'vet', 'veterinary doctor', 'animal doctor'],
        'weight': 1.0
    },
    {
        'role': 'Dairy Farm Manager',
        'key_skills': ['dairy farming', 'livestock management', 'milk production', 'animal husbandry'],
        'patterns': ['dairy farm manager', 'dairy manager', 'livestock manager'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Fashion Designer',
        'key_skills': ['fashion design', 'sketching', 'pattern making', 'garment construction', 'textiles'],
        'patterns': ['fashion designer', 'clothing designer', 'apparel designer'],
        'weight': 1.0
    },
    {
        'role': 'Textile Engineer',
        'key_skills': ['textile engineering', 'fabric technology', 'quality control', 'textile testing'],
        'patterns': ['textile engineer', 'textile technologist', 'fabric engineer'],
        'weight': 1.0
    },
    {
        'role': 'Merchandiser (Fashion)',
        'key_skills': ['fashion merchandising', 'buying', 'trend analysis', 'product development', 'vendor management'],
        'patterns': ['fashion merchandiser', 'apparel merchandiser', 'garment merchandiser'],
        'weight': 1.0
    },
    {
        'role': 'Pattern Maker',
        'key_skills': ['pattern making', 'garment construction', 'technical drawing', 'fashion design'],
        'patterns': ['pattern maker', 'pattern cutter', 'garment technician'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Video Editor',
        'key_skills': ['video editing', 'adobe premiere', 'final cut pro', 'after effects', 'color grading'],
        'patterns': ['video editor', 'film editor', 'post production editor'],
        'weight': 1.0
    },
    {
        'role': 'Content Writer',
        'key_skills': ['content writing', 'copywriting', 'seo writing', 'blogging', 'creative writing'],
        'patterns': ['content writer', 'copywriter', 'writer', 'content creator'],
        'weight': 1.0
    },
    {
        'role': 'Journalist',
        'key_skills': ['journalism', 'reporting', 'news writing', 'interviewing', 'research'],
        'patterns': ['journalist', 'reporter', 'news reporter', 'correspondent'],
        'weight': 1.0
    },
    {
        'role': 'Photographer',
        'key_skills': ['photography', 'photo editing', 'lightroom', 'photoshop', 'lighting', 'composition'],
        'patterns': ['photographer', 'commercial photographer', 'wedding photographer'],
        'weight': 1.0
    },
    {
        'role': 'Cinematographer',
        'key_skills': ['cinematography', 'camera operation', 'lighting', 'shot composition', 'filmmaking'],
        'patterns': ['cinematographer', 'director of photography', 'dop', 'camera operator'],
        'weight': 1.0
    },
    {
        'role': 'Sound Engineer',
        'key_skills': ['audio engineering', 'sound mixing', 'recording', 'pro tools', 'sound design'],
        'patterns': ['sound engineer', 'audio engineer', 'sound technician', 'mixing engineer'],
        'weight': 1.0
    },
    {
        'role': 'Radio Jockey (RJ)',
        'key_skills': ['radio broadcasting', 'voice modulation', 'entertainment', 'communication', 'hosting'],
        'patterns': ['radio jockey', 'rj', 'radio host', 'radio presenter'],
        'weight': 1.0
    },
    {
        'role': 'Anchor / TV Presenter',
        'key_skills': ['anchoring', 'presentation', 'communication', 'hosting', 'broadcasting'],
        'patterns': ['anchor', 'tv anchor', 'tv presenter', 'news anchor', 'host'],
        'weight': 1.0
    },
    {
        'role': 'Actor',
        'key_skills': ['acting', 'performance', 'theatre', 'improvisation', 'voice modulation'],
        'patterns': ['actor', 'actress', 'theatre artist', 'performer'],
        'weight': 1.0
    },
    {
        'role': 'Director',
        'key_skills': ['directing', 'filmmaking', 'storytelling', 'shot composition', 'production'],
        'patterns': ['director', 'film director', 'creative director media'],
        'weight': 1.0
    },
    {
        'role': 'Animation Artist',
        'key_skills': ['animation', '2d animation', '3d animation', 'maya', 'blender', 'character design'],
        'patterns': ['animator', 'animation artist', '3d animator', '2d animator'],
        'weight': 1.0
    },
    {
        'role': 'VFX Artist',
        'key_skills': ['vfx', 'visual effects', 'compositing', 'nuke', 'after effects', 'cg'],
        'patterns': ['vfx artist', 'visual effects artist', 'compositing artist'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Personal Trainer',
        'key_skills': ['fitness training', 'exercise programs', 'nutrition', 'strength training', 'cardio'],
        'patterns': ['personal trainer', 'fitness trainer', 'gym trainer', 'fitness coach'],
        'weight': 1.0
    },
    {
        'role': 'Sports Coach',
        'key_skills': ['coaching', 'sports training', 'athlete development', 'strategy', 'motivation'],
        'patterns': ['sports coach', 'coach', 'athletic coach', 'team coach'],
        'weight': 1.0
    },
    {
        'role': 'Yoga Instructor',
        'key_skills': ['yoga', 'asanas', 'meditation', 'pranayama', 'wellness', 'fitness'],
        'patterns': ['yoga instructor', 'yoga teacher', 'yoga trainer'],
        'weight': 1.0
    },
    {
        'role': 'Physiotherapist',
        'key_skills': ['physiotherapy', 'rehabilitation', 'exercise therapy', 'sports injuries', 'manual therapy'],
        'patterns': ['physiotherapist', 'physical therapist', 'rehab specialist'],
        'weight': 1.0
    },
    {
        'role': 'Sports Manager',
        'key_skills': ['sports management', 'event management', 'athlete management', 'sports marketing'],
        'patterns': ['sports manager', 'sports administrator', 'athletic director'],
        'weight': 1.0
    },
    {
        'role': 'Dietitian / Nutritionist',
        'key_skills': ['nutrition', 'diet planning', 'meal planning', 'health assessment', 'weight management'],
        'patterns': ['dietitian', 'nutritionist', 'diet consultant', 'nutrition specialist'],
        'weight': 1.0
    },
    
    {
        'role': 'Beautician / Cosmetologist',
        'key_skills': ['beauty treatments', 'makeup', 'skincare', 'hair styling', 'facials'],
        'patterns': ['beautician', 'cosmetologist', 'beauty therapist', 'makeup artist'],
        'weight': 1.0
    },
    {
        'role': 'Hair Stylist',
        'key_skills': ['hair styling', 'hair cutting', 'hair coloring', 'salon management'],
        'patterns': ['hair stylist', 'hairdresser', 'hairstylist', 'salon professional'],
        'weight': 1.0
    },
    {
        'role': 'Salesforce Developer',
        'key_skills': ['salesforce', 'apex', 'visualforce', 'lightning', 'crm', 'soql'],
        'patterns': ['salesforce developer', 'salesforce engineer', 'sfdc developer'],
        'weight': 1.0
    },
    {
        'role': 'SAP Consultant',
        'key_skills': ['sap', 'abap', 'sap hana', 'sap mm', 'sap sd', 'sap fico'],
        'patterns': ['sap consultant', 'sap developer', 'sap functional', 'sap technical'],
        'weight': 1.0
    },
    {
        'role': 'Oracle Developer',
        'key_skills': ['oracle', 'pl/sql', 'oracle forms', 'oracle reports', 'database'],
        'patterns': ['oracle developer', 'oracle consultant', 'pl/sql developer'],
        'weight': 1.0
    },
    {
        'role': 'Shopify Developer',
        'key_skills': ['shopify', 'liquid', 'e-commerce', 'shopify apps', 'theme development'],
        'patterns': ['shopify developer', 'shopify expert', 'shopify theme developer'],
        'weight': 1.0
    },
    {
        'role': 'WordPress Developer',
        'key_skills': ['wordpress', 'php', 'mysql', 'woocommerce', 'theme development', 'plugin development'],
        'patterns': ['wordpress developer', 'wp developer', 'wordpress theme developer'],
        'weight': 1.0
    },
    {
        'role': 'RPA Developer',
        'key_skills': ['rpa', 'uipath', 'automation anywhere', 'blue prism', 'process automation'],
        'patterns': ['rpa developer', 'automation developer', 'uipath developer'],
        'weight': 1.0
    },
    {
        'role': 'ServiceNow Developer',
        'key_skills': ['servicenow', 'itsm', 'javascript', 'workflows', 'service portal'],
        'patterns': ['servicenow developer', 'servicenow consultant', 'snow developer'],
        'weight': 1.0
    },
    {
        'role': 'Workday Consultant',
        'key_skills': ['workday', 'hcm', 'financials', 'integration', 'workday studio'],
        'patterns': ['workday consultant', 'workday developer', 'workday specialist'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Investment Banker',
        'key_skills': ['investment banking', 'financial modeling', 'valuation', 'mergers acquisitions', 'capital markets'],
        'patterns': ['investment banker', 'ib analyst', 'investment banking analyst'],
        'weight': 1.0
    },
    {
        'role': 'Equity Research Analyst',
        'key_skills': ['equity research', 'financial analysis', 'stock analysis', 'valuation', 'modeling'],
        'patterns': ['equity research analyst', 'equity analyst', 'research analyst'],
        'weight': 1.0
    },
    {
        'role': 'Credit Analyst',
        'key_skills': ['credit analysis', 'risk assessment', 'financial modeling', 'loan evaluation'],
        'patterns': ['credit analyst', 'credit risk analyst', 'loan analyst'],
        'weight': 1.0
    },
    {
        'role': 'Portfolio Manager',
        'key_skills': ['portfolio management', 'asset allocation', 'investment strategy', 'risk management'],
        'patterns': ['portfolio manager', 'fund manager', 'investment manager'],
        'weight': 1.0
    },
    {
        'role': 'Risk Manager',
        'key_skills': ['risk management', 'risk assessment', 'compliance', 'regulatory', 'internal controls'],
        'patterns': ['risk manager', 'risk analyst', 'enterprise risk manager'],
        'weight': 1.0
    },
    {
        'role': 'Actuary',
        'key_skills': ['actuarial science', 'statistics', 'risk modeling', 'insurance', 'pension'],
        'patterns': ['actuary', 'actuarial analyst', 'actuarial consultant'],
        'weight': 1.0
    },
    {
        'role': 'Treasury Manager',
        'key_skills': ['treasury management', 'cash management', 'liquidity', 'forex', 'financial planning'],
        'patterns': ['treasury manager', 'treasury analyst', 'cash manager'],
        'weight': 1.0
    },
    {
        'role': 'Tax Consultant',
        'key_skills': ['taxation', 'tax planning', 'gst', 'income tax', 'tax compliance'],
        'patterns': ['tax consultant', 'tax advisor', 'tax manager'],
        'weight': 1.0
    },
    {
        'role': 'Compliance Officer',
        'key_skills': ['compliance', 'regulatory', 'aml', 'kyc', 'risk management', 'audit'],
        'patterns': ['compliance officer', 'compliance manager', 'regulatory compliance'],
        'weight': 1.0
    },
    {
        'role': 'Insurance Underwriter',
        'key_skills': ['underwriting', 'risk assessment', 'insurance', 'policy analysis'],
        'patterns': ['underwriter', 'insurance underwriter', 'underwriting analyst'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Corporate Lawyer',
        'key_skills': ['corporate law', 'contract law', 'mergers acquisitions', 'compliance', 'legal drafting'],
        'patterns': ['corporate lawyer', 'corporate counsel', 'in-house counsel'],
        'weight': 1.0
    },
    {
        'role': 'Legal Advisor',
        'key_skills': ['legal advisory', 'contract review', 'legal compliance', 'litigation support'],
        'patterns': ['legal advisor', 'legal consultant', 'legal analyst'],
        'weight': 1.0
    },
    {
        'role': 'Patent Attorney',
        'key_skills': ['patent law', 'intellectual property', 'patent drafting', 'trademark', 'ip litigation'],
        'patterns': ['patent attorney', 'ip attorney', 'patent agent'],
        'weight': 1.0
    },
    
   
    {
        'role': 'Research Scientist',
        'key_skills': ['research', 'scientific analysis', 'data analysis', 'publications', 'experimentation'],
        'patterns': ['research scientist', 'scientist', 'research associate', 'researcher'],
        'weight': 1.0
    },
    {
        'role': 'Professor',
        'key_skills': ['teaching', 'research', 'curriculum development', 'academic writing', 'mentoring'],
        'patterns': ['professor', 'assistant professor', 'associate professor'],
        'weight': 1.0
    },
    {
        'role': 'Librarian',
        'key_skills': ['library management', 'cataloging', 'information management', 'research assistance'],
        'patterns': ['librarian', 'library manager', 'information specialist'],
        'weight': 1.0
    },
    {
        'role': 'Educational Counselor',
        'key_skills': ['counseling', 'career guidance', 'student advising', 'educational planning'],
        'patterns': ['educational counselor', 'career counselor', 'academic counselor'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Social Worker',
        'key_skills': ['social work', 'community development', 'counseling', 'case management', 'advocacy'],
        'patterns': ['social worker', 'community worker', 'welfare officer'],
        'weight': 1.0
    },
    {
        'role': 'NGO Program Manager',
        'key_skills': ['program management', 'ngo operations', 'project coordination', 'fundraising', 'community development'],
        'patterns': ['ngo program manager', 'development officer', 'project manager ngo'],
        'weight': 1.0
    },
    
   
    {
        'role': 'Real Estate Agent',
        'key_skills': ['real estate', 'property sales', 'negotiation', 'market analysis', 'client relations'],
        'patterns': ['real estate agent', 'property consultant', 'realtor'],
        'weight': 1.0
    },
    {
        'role': 'Property Manager',
        'key_skills': ['property management', 'tenant relations', 'maintenance', 'lease administration'],
        'patterns': ['property manager', 'facility manager', 'building manager'],
        'weight': 1.0
    },
    
   
    {
        'role': 'Insurance Agent',
        'key_skills': ['insurance sales', 'policy advising', 'customer service', 'claims processing'],
        'patterns': ['insurance agent', 'insurance advisor', 'lic agent'],
        'weight': 1.0
    },
    {
        'role': 'Claims Adjuster',
        'key_skills': ['claims processing', 'investigation', 'damage assessment', 'negotiation'],
        'patterns': ['claims adjuster', 'claims examiner', 'insurance adjuster'],
        'weight': 1.0
    },
    
    
    {
        'role': 'Game Designer',
        'key_skills': ['game design', 'level design', 'game mechanics', 'storytelling', 'prototyping'],
        'patterns': ['game designer', 'level designer', 'gameplay designer'],
        'weight': 1.0
    },
    {
        'role': 'Musician',
        'key_skills': ['music', 'performance', 'composition', 'music theory', 'instruments'],
        'patterns': ['musician', 'music artist', 'composer', 'singer'],
        'weight': 1.0
    },
    
  
    {
        'role': 'Aircraft Loadmaster',
        'key_skills': ['load planning', 'weight and balance', 'cargo operations', 'aircraft loading'],
        'patterns': ['loadmaster', 'cargo specialist', 'load planner'],
        'weight': 1.0
    },
    
   
    {
        'role': 'Warehouse Manager',
        'key_skills': ['warehouse management', 'inventory', 'logistics', 'operations', 'wms'],
        'patterns': ['warehouse manager', 'warehouse supervisor', 'warehouse operations'],
        'weight': 1.0
    },
    {
        'role': 'Logistics Coordinator',
        'key_skills': ['logistics', 'supply chain', 'coordination', 'shipping', 'transportation'],
        'patterns': ['logistics coordinator', 'logistics executive', 'logistics analyst'],
        'weight': 1.0
    },
    {
        'role': 'Customs Officer',
        'key_skills': ['customs clearance', 'import export', 'documentation', 'compliance', 'trade regulations'],
        'patterns': ['customs officer', 'customs executive', 'customs specialist'],
        'weight': 1.0
    },
    
 
    {
        'role': 'Ship Captain',
        'key_skills': ['navigation', 'maritime operations', 'crew management', 'safety', 'ship handling'],
        'patterns': ['ship captain', 'master mariner', 'ship master'],
        'weight': 1.0
    },
    {
        'role': 'Port Manager',
        'key_skills': ['port operations', 'cargo handling', 'logistics', 'maritime management'],
        'patterns': ['port manager', 'harbor master', 'port operations manager'],
        'weight': 1.0
    },
    
 
    {
        'role': 'Mining Engineer',
        'key_skills': ['mining', 'excavation', 'mineral processing', 'mine planning', 'safety'],
        'patterns': ['mining engineer', 'mine engineer', 'mining professional'],
        'weight': 1.0
    },
    {
        'role': 'Geologist',
        'key_skills': ['geology', 'geological survey', 'mineral exploration', 'rock analysis'],
        'patterns': ['geologist', 'exploration geologist', 'geological engineer'],
        'weight': 1.0
    },
    
  
    {
        'role': 'Translator',
        'key_skills': ['translation', 'language proficiency', 'localization', 'interpretation'],
        'patterns': ['translator', 'language translator', 'localization specialist'],
        'weight': 1.0
    },
    {
        'role': 'Interpreter',
        'key_skills': ['interpretation', 'language proficiency', 'simultaneous interpretation', 'communication'],
        'patterns': ['interpreter', 'language interpreter', 'conference interpreter'],
        'weight': 1.0
    }
        ]

        
        # STEP 1: Find Primary Match (becomes Priority 1)
        primary_match = None
        primary_score = 0
        
        for role_pattern in role_detection_patterns:
            role_name = role_pattern['role']
            patterns = role_pattern['patterns']
            key_skills = role_pattern['key_skills']
            
            # Calculate match score for this role
            pattern_matches = 0
            skill_matches = 0
            
            # Check pattern matches in job title/description
            for pattern in patterns:
                if pattern in all_text:
                    pattern_matches += 1
            
            # Check skill matches in primary skills
            if primary_skills:
                for skill in key_skills:
                    if any(skill.lower() in ps.lower() for ps in primary_skills):
                        skill_matches += 1
            
            # Calculate total match score
            total_score = (pattern_matches * 2) + skill_matches  # Pattern matches get 2x weight
            
            # Check if this is the best match so far
            if total_score > primary_score:
                primary_score = total_score
                primary_match = role_pattern.copy()
        
        # STEP 2: Set Primary Match as Priority 1
        if primary_match and primary_score > 0:
            primary_match['priority'] = 1
            priorities.append(primary_match)
        
        # STEP 3: Find Secondary Matches (Priority 2 & 3)
        if len(priorities) < 3:
            secondary_candidates = []
            
            for role_pattern in role_detection_patterns:
                # Skip if this is already the primary match
                if primary_match and role_pattern['role'] == primary_match['role']:
                    continue
                
                role_name = role_pattern['role']
                patterns = role_pattern['patterns']
                key_skills = role_pattern['key_skills']
                
                # Calculate secondary match score
                pattern_matches = sum(1 for pattern in patterns if pattern in all_text)
                skill_matches = 0
                
                # Check in secondary skills
                if secondary_skills:
                    for skill in key_skills:
                        if any(skill.lower() in ss.lower() for ss in secondary_skills):
                            skill_matches += 1
                
                # Also check in primary skills but with lower weight
                if primary_skills:
                    for skill in key_skills:
                        if any(skill.lower() in ps.lower() for ps in primary_skills):
                            skill_matches += 0.5
                
                total_score = pattern_matches + skill_matches
                
                if total_score > 0:
                    secondary_candidates.append({
                        'role_pattern': role_pattern.copy(),
                        'score': total_score
                    })
            
            # Sort secondary candidates by score and add top 2
            secondary_candidates.sort(key=lambda x: x['score'], reverse=True)
            
            for i, candidate in enumerate(secondary_candidates[:2]):
                role_pattern = candidate['role_pattern']
                priority_level = i + 2  # Priority 2, 3
                role_pattern['priority'] = priority_level
                role_pattern['weight'] = 0.8 if priority_level == 2 else 0.6
                priorities.append(role_pattern)
        
        # FALLBACK 1: Use Primary Skills if no matches
        if not priorities and primary_skills:
            # Determine role from primary skills
            primary_skills_lower = [skill.lower() for skill in primary_skills]
            
            # Technology-based role detection
            role_mappings = [
                (['python', 'django', 'flask', 'fastapi'], 'Python Developer', ['python', 'django', 'flask', 'fastapi']),
                (['java', 'spring', 'hibernate', 'jsp'], 'Java Developer', ['java', 'spring', 'hibernate', 'maven']),
                (['.net', 'c#', 'asp.net', 'mvc'], '.NET Developer', ['c#', '.net', 'asp.net', 'mvc']),
                (['javascript', 'react', 'angular', 'vue', 'node.js'], 'JavaScript Developer', ['javascript', 'react', 'angular', 'node.js']),
                (['php', 'laravel', 'codeigniter'], 'PHP Developer', ['php', 'laravel', 'mysql']),
                (['docker', 'kubernetes', 'jenkins', 'terraform', 'aws'], 'DevOps Engineer', ['docker', 'kubernetes', 'aws', 'jenkins']),
                (['android', 'ios', 'react native', 'flutter'], 'Mobile Developer', ['android', 'ios', 'react native', 'flutter'])
            ]
            
            best_role = None
            best_match_count = 0
            
            for tech_list, role_name, key_skills in role_mappings:
                match_count = sum(1 for tech in tech_list if any(tech in skill for skill in primary_skills_lower))
                if match_count > best_match_count:
                    best_match_count = match_count
                    best_role = (role_name, key_skills)
            
            if best_role:
                role_name, key_skills = best_role
                priorities.append({
                    'role': role_name,
                    'priority': 1,
                    'key_skills': key_skills,
                    'weight': 1.0
                })
            else:
                # Use all primary skills as Software Developer
                priorities.append({
                    'role': 'Software Developer',
                    'priority': 1,
                    'key_skills': primary_skills[:8],  # First 8 primary skills
                    'weight': 1.0
                })
        
        # FINAL FALLBACK: Generic Software Developer
        if not priorities:
            priorities.append({
                'role': 'Software Developer',
                'priority': 1,
                'key_skills': ['programming', 'software development', 'coding', 'problem solving'],
                'weight': 1.0
            })
        
        return priorities
    
    def _parse_experience_years(self, exp_str: str) -> float:
        # Parse experience years from string
        if not exp_str:
            return 0.0
        
        exp_str = str(exp_str).lower().strip()
        
        patterns = [
            r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)',
            r'(\d+(?:\.\d+)?)(?:-\d+(?:\.\d+)?)?\s*(?:years?|yrs?)',
            r'(\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, exp_str)
            if match:
                return float(match.group(1))
        
        return 0.0
    
    def _extract_years_from_duration(self, duration_str: str) -> float:
        # Extract years from duration string with enhanced parsing
        
        if not duration_str:
            return 0.5
        
        duration_str = duration_str.lower().strip()
        
        
        present_patterns = [
            r'(\w+)\s+(\d{4})\s*[-–]\s*present',
            r'(\d{4})\s*[-–]\s*present',
            r'(\d{1,2})/(\d{4})\s*[-–]\s*present'
        ]
        
        for pattern in present_patterns:
            match = re.search(pattern, duration_str)
            if match:
                if len(match.groups()) == 2 and match.group(2).isdigit():
                    start_year = int(match.group(2))
                    current_year = datetime.now().year
                    return max(0.1, current_year - start_year)
        
        # Handle year ranges
        year_range_patterns = [
            r'(\d{4})\s*[-–]\s*(\d{4})',
            r'\w+\s+(\d{4})\s*[-–]\s*\w+\s+(\d{4})',
            r'(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})/(\d{4})'
        ]
        
        for pattern in year_range_patterns:
            match = re.search(pattern, duration_str)
            if match:
                if pattern == r'(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})/(\d{4})':
                    start_year = int(match.group(2))
                    end_year = int(match.group(4))
                else:
                    start_year = int(match.group(1))
                    end_year = int(match.group(2))
                return max(0.1, end_year - start_year + 1)
        
        # Handle explicit years/months
        years_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', duration_str)
        if years_match:
            return float(years_match.group(1))
        
        months_match = re.search(r'(\d+)\s*months?', duration_str)
        if months_match:
            return max(0.1, int(months_match.group(1)) / 12)
        
        return 1.0
    
    def _get_default_score(self, error_msg: str) -> dict:
        # Default score structure
        return {
            "overall_score": 0,
            "skill_match_score": 0,
            "experience_score": 0,
            "detailed_analysis": {"error": error_msg}
        }
