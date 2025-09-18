import spacy
from typing import Dict, List, Any, Tuple
import re
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
import traceback

class MatchingEngine:
    def __init__(self):
        """Initialize the enhanced matching engine with experience requirement matching"""
        try:
            try:
                self.nlp = spacy.load("en_core_web_md")
                print("✅ spaCy medium model loaded successfully")
            except OSError:
                self.nlp = spacy.load("en_core_web_sm")
                print("✅ spaCy small model loaded as fallback")
        except OSError:
            print("⚠️ spaCy model not found, using basic matching")
            self.nlp = None
    
    def calculate_ats_score(self, jd_data: dict, resume_data: dict, skills_weightage: dict, manual_priorities: List[Dict] = None) -> dict:
        """Calculate enhanced ATS score with experience requirement matching"""
        
        print(f"🎯 Starting FINAL ATS scoring with experience requirements...")
        print(f"📋 JD data available: {bool(jd_data)}")
        print(f"📄 Resume data available: {bool(resume_data)}")
        print(f"🎯 Manual priorities provided: {bool(manual_priorities)}")
        
        if not jd_data or not resume_data:
            return self._get_default_score("Missing JD or resume data")
        
        try:
            # Extract JD experience requirement
            jd_experience_required = self._extract_experience_requirement(jd_data)
            print(f"📋 JD Experience Required: {jd_experience_required} years")
            
            # Extract job role priorities
            job_priorities = self._extract_job_priorities(jd_data, manual_priorities)
            print(f"🎯 Job Priorities: {[(p['role'], p['priority']) for p in job_priorities]}")
            
            # Enhanced: Parse resume skills properly
            resume_skills = self._extract_resume_skills(resume_data)
            print(f"📄 Extracted Resume Skills: {len(resume_skills)} skills")
            
            # Enhanced: Parse experience with description analysis
            enhanced_experience = self._enhance_experience_data(resume_data, job_priorities)
            print(f"🏢 Enhanced Experience Timeline: {len(enhanced_experience)} jobs")
            
            # Update resume data with enhanced information
            enhanced_resume_data = resume_data.copy()
            enhanced_resume_data['skills'] = resume_skills
            enhanced_resume_data['experience_timeline'] = enhanced_experience
            
            # SCORE 1: Complete Skills Matching (0-100 points)
            skills_score = self._calculate_complete_skills_score(
                enhanced_resume_data, job_priorities, skills_weightage
            )
            
            # SCORE 2: Enhanced Experience Matching with JD Requirements (0-100 points)
            experience_score = self._calculate_enhanced_experience_score(
                enhanced_resume_data, job_priorities, jd_experience_required
            )
            
            # FINAL SCORE CALCULATION
            total_experience = enhanced_resume_data.get('total_experience', 0)
            experience_timeline = enhanced_experience
            
            # Determine if candidate is fresh graduate
            is_fresh_graduate = (total_experience == 0 or not experience_timeline)
            
            if is_fresh_graduate:
                # Fresh graduates: Use skills score with penalty if experience required
                if jd_experience_required > 0:
                    # Apply penalty for missing experience
                    penalty = min(30, jd_experience_required * 10)  # Max 30% penalty
                    final_score = max(0, skills_score - penalty)
                    score_method = f"Skills-Based with {penalty}% experience penalty"
                else:
                    final_score = skills_score
                    score_method = "Skills-Based (No experience required)"
                print(f"🎓 Fresh Graduate - Score: {final_score:.2f}%")
            else:
                # Experienced candidates: Average of both scores
                final_score = (skills_score + experience_score) / 2
                score_method = "Skills + Experience Average"
                print(f"👨‍💼 Experienced - Average Score: ({skills_score:.1f}% + {experience_score:.1f}%) ÷ 2 = {final_score:.2f}%")
            
            # Detailed analysis
            detailed_analysis = {
                "job_priorities": job_priorities,
                "jd_experience_required": jd_experience_required,
                "candidate_total_experience": total_experience,
                "scoring_method": score_method,
                "is_fresh_graduate": is_fresh_graduate,
                "enhanced_skills": resume_skills,
                "enhanced_experience": enhanced_experience,
                "skills_analysis": self._get_complete_skills_analysis(enhanced_resume_data, job_priorities, skills_weightage),
                "experience_analysis": self._get_enhanced_experience_analysis(enhanced_resume_data, job_priorities, jd_experience_required),
                "scoring_breakdown": {
                    "skills_score": round(skills_score, 2),
                    "experience_score": round(experience_score, 2),
                    "final_score": round(final_score, 2),
                    "scoring_method": score_method,
                    "meets_experience_requirement": total_experience >= jd_experience_required
                }
            }
            
            print(f"🎯 FINAL ATS Score: {final_score:.2f}%")
            print(f"📊 Skills: {skills_score:.1f}/100 | Experience: {experience_score:.1f}/100")
            print(f"📋 Experience Requirement: {jd_experience_required} years | Candidate: {total_experience} years")
            
            return {
                "overall_score": round(min(100, max(0, final_score)), 2),
                "skill_match_score": round(skills_score, 2),
                "experience_score": round(experience_score, 2),
                "qualification_score": 75.0,
                "detailed_analysis": detailed_analysis
            }
            
        except Exception as e:
            print(f"❌ Error in final matching calculation: {str(e)}")
            traceback.print_exc()
            return self._get_default_score(str(e))
    
    # Extract Experience Requirement from JD
    def _extract_experience_requirement(self, jd_data: Dict) -> float:
        """Extract experience requirement from job description"""
        
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
                    # Range like "2-5 years" - take minimum
                    return float(matches[0][0])
                else:
                    # Single number like "3+ years"
                    return float(matches[0])
        
        # Default: No specific experience required
        return 0.0
    
    # Extract Resume Skills
    def _extract_resume_skills(self, resume_data: Dict) -> List[str]:
        """Extract and normalize skills from resume with multiple sources"""
        
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
        """Extract technologies from job description text"""
        
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
        
        # Search for all technology patterns
        for category, techs in tech_patterns.items():
            for tech in techs:
                pattern = r'\b' + re.escape(tech.lower()) + r'\b'
                if re.search(pattern, desc_lower):
                    found_techs.append(tech)
        
        # Also search for priority skills specifically
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
            print("❌ No skills found in resume - Skills Score: 0/100")
            return 0.0
        
        print(f"🎯 SKILLS SCORING:")
        
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
        print(f"  📋 Total Skills Required: {total_required_skills}")
        
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
            config_weight = metadata['config_weight'] / 100  # Convert to 0-1
            
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
                print(f"    ✅ {required_skill} (P{priority_level}) - Weight: {final_weight:.3f}")
            else:
                missing_skills.append(required_skill)
                print(f"    ❌ {required_skill} (P{priority_level}) - Missing")
        
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
        
        print(f"  📊 Skills: {len(matched_skills)}/{total_required_skills} matched ({coverage_ratio*100:.1f}%)")
        print(f"  📊 Score: {base_skills_score:.1f} + {coverage_bonus} + {priority_bonus} = {final_skills_score:.1f}/100")
        
        return final_skills_score
    
    # SCORE 2: Enhanced Experience Matching with JD Requirements
    def _calculate_enhanced_experience_score(self, resume_data: Dict, job_priorities: List[Dict], jd_experience_required: float) -> float:
        """Calculate enhanced experience score with JD requirement matching (0-100 points)"""
        
        experience_timeline = resume_data.get('experience_timeline', [])
        total_experience = resume_data.get('total_experience', 0)
        
        print(f"🏢 ENHANCED EXPERIENCE SCORING:")
        print(f"  📅 Total Experience: {total_experience} years")
        print(f"  📋 JD Required Experience: {jd_experience_required} years")
        print(f"  📋 Experience Timeline: {len(experience_timeline)} jobs")
        
        # Handle fresh graduates
        if not experience_timeline or total_experience == 0:
            if jd_experience_required == 0:
                print("  🎓 Fresh Graduate + No Experience Required = 50/100")
                return 50.0  # Neutral score when no experience required
            else:
                print("  🎓 Fresh Graduate but Experience Required = 10/100")
                return 10.0  # Low score when experience is required
        
        # STEP 1: Experience Requirement Matching Score (40% weight)
        experience_requirement_score = self._calculate_experience_requirement_score(total_experience, jd_experience_required)
        
        # STEP 2: Relevant Experience Score (40% weight)
        relevant_experience_score = self._calculate_relevant_experience_score(experience_timeline, job_priorities)
        
        # STEP 3: Recent/Current Experience Bonus (20% weight)
        recent_experience_bonus = self._calculate_recent_experience_bonus(experience_timeline, job_priorities)
        
        # Final experience score calculation
        final_experience_score = (
            experience_requirement_score * 0.4 +
            relevant_experience_score * 0.4 +
            recent_experience_bonus * 0.2
        )
        
        print(f"  📊 Experience Breakdown:")
        print(f"    • Requirement Match: {experience_requirement_score:.1f}/100 (40% weight)")
        print(f"    • Relevant Experience: {relevant_experience_score:.1f}/100 (40% weight)")
        print(f"    • Recent/Current Bonus: {recent_experience_bonus:.1f}/100 (20% weight)")
        print(f"    • Final Experience Score: {final_experience_score:.1f}/100")
        
        return min(100, max(0, final_experience_score))
    
    def _calculate_experience_requirement_score(self, total_experience: float, jd_experience_required: float) -> float:
        """Calculate score based on JD experience requirement"""
        
        if jd_experience_required == 0:
            # No specific experience required
            return 100.0
        
        if total_experience >= jd_experience_required:
            # Meets or exceeds requirement
            if total_experience >= jd_experience_required * 1.5:
                return 100.0  # 150%+ of required = Perfect score
            else:
                # Linear scale from meets requirement to 150%
                excess_ratio = (total_experience - jd_experience_required) / (jd_experience_required * 0.5)
                return 85 + (excess_ratio * 15)  # 85-100 range
        else:
            # Below requirement
            if total_experience >= jd_experience_required * 0.8:
                # 80-100% of requirement
                ratio = total_experience / jd_experience_required
                return 60 + ((ratio - 0.8) * 125)  # 60-85 range
            elif total_experience >= jd_experience_required * 0.5:
                # 50-80% of requirement
                ratio = total_experience / jd_experience_required
                return 30 + ((ratio - 0.5) * 100)  # 30-60 range
            else:
                # Less than 50% of requirement
                ratio = total_experience / jd_experience_required
                return ratio * 60  # 0-30 range

    def _calculate_relevant_experience_score(self, experience_timeline: List[Dict], job_priorities: List[Dict]) -> float:
        """Calculate score based on relevant experience in priority technologies - ENHANCED"""
        
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
                role_keywords = role_name.lower().replace(' developer', '').replace(' engineer', '').split()
                for keyword in role_keywords:
                    if keyword in exp_role:
                        # More specific matches get higher scores
                        if keyword in ['python', 'java', 'javascript', 'react', 'angular', '.net', 'php']:
                            role_match_score += 2  # Technology-specific roles
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
        """Calculate bonus for recent/current experience in priority technologies"""
        
        if not experience_timeline or not job_priorities:
            return 0.0
        
        current_year = datetime.now().year
        max_bonus = 0
        
        for experience in experience_timeline:
            exp_duration = experience.get('duration', '').lower()
            exp_technologies = [tech.lower().strip() for tech in experience.get('technologies_used', [])]
            
            # Check if recent/current
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
        """Enhanced skill matching"""
        
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
        """Enhanced technology matching"""
        
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
        """Enhanced synonym matching for skills"""
        
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
        """Fuzzy matching for skills"""
        
        if len(skill1) < 3 or len(skill2) < 3:
            return False
        
        # Character overlap ratio
        overlap = len(set(skill1) & set(skill2))
        min_length = min(len(skill1), len(skill2))
        
        if overlap / min_length > 0.8:  # 80% character overlap
            return True
        
        # spaCy semantic similarity
        if self.nlp:
            try:
                doc1 = self.nlp(skill1)
                doc2 = self.nlp(skill2)
                similarity = doc1.similarity(doc2)
                return similarity > 0.85  # High similarity threshold
            except:
                pass
        
        return False
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill for consistent matching"""
        
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
            'resume_skills': resume_skills[:20],  # First 20 skills
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
        """Enhanced experience analysis with JD requirement matching"""
        
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
        """Categorize experience strength"""
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
            print(f"🎯 Using MANUAL priorities: {len(manual_priorities)} specified")
            return manual_priorities
        
        print(f"🤖 Using AUTO-DETECTED priorities")
        return self._auto_detect_job_priorities(jd_data)
    
    def _auto_detect_job_priorities(self, jd_data: Dict) -> List[Dict]:
        """Auto-detect priorities from JD dynamically based on actual requirements"""
        
        job_title = jd_data.get('job_title', '').lower()
        job_description = jd_data.get('description', '').lower()
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        
        all_text = f"{job_title} {job_description}"
        priorities = []
        
        # DYNAMIC ROLE DETECTION - All roles compete for Priority 1
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
        if len(priorities) < 3:  # Add up to 2 more priorities
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
        """Parse experience years from string"""
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
        """Extract years from duration string with enhanced parsing"""
        
        if not duration_str:
            return 0.5
        
        duration_str = duration_str.lower().strip()
        
        # Handle "Mar 2022 - Present" format
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
        """Default score structure"""
        return {
            "overall_score": 0,
            "skill_match_score": 0,
            "experience_score": 0,
            "detailed_analysis": {"error": error_msg}
        }

