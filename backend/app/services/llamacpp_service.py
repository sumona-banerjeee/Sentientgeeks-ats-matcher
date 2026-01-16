import json
import re
from typing import Dict, Any, List
from openai import OpenAI
from backend.app.config import settings


class LlamaCppService:
    """
    Enhanced service for intelligent ATS matching via llama.cpp
    SMART VERSION: Semantic skill matching, proper scoring, no unfair zeros
    """
    
    def __init__(self):
        if not settings.LLAMACPP_BASE_URL:
            raise ValueError("LLAMACPP_BASE_URL not configured in .env")
        
        if not settings.LLAMACPP_MODEL:
            raise ValueError("LLAMACPP_MODEL not configured in .env")
        
        self.client = OpenAI(
            base_url=settings.LLAMACPP_BASE_URL,
            api_key=settings.LLAMACPP_API_KEY,
            timeout=settings.LLAMACPP_TIMEOUT
        )
        
        self.model = settings.LLAMACPP_MODEL
        
        print(f"Enhanced LlamaCppService initialized (SMART VERSION)")
        print(f"   Base URL: {settings.LLAMACPP_BASE_URL}")
        print(f"   Model: {self.model}")
    
    def _make_request(
        self, 
        prompt: str, 
        system_prompt: str = None, 
        temperature: float = 0.2,
        enable_thinking: bool = False
    ) -> str:
        """Make a request to llama.cpp server"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            print(f"llama.cpp Request")
            print(f"   Prompt Length: {len(prompt)} chars")
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2000
            }
            
            if hasattr(self.client, 'with_options'):
                kwargs["extra_body"] = {
                    "chat_template_kwargs": {"enable_thinking": enable_thinking}
                }
            
            completion = self.client.chat.completions.create(**kwargs)
            
            full_text = completion.choices[0].message.content
            
            if "Provide answer." in full_text:
                final_answer = full_text.split("Provide answer.")[-1].strip()
            else:
                final_answer = full_text
            
            print(f"llama.cpp Response: {len(final_answer)} chars")
            
            return final_answer.strip()
        
        except Exception as e:
            raise Exception(f"llama.cpp request failed: {str(e)}")
    
    def enhanced_skill_matching(
        self, 
        resume_data: dict,
        resume_skills: list, 
        jd_primary_skills: list, 
        jd_secondary_skills: list,
        skills_weightage: dict,
        experience_timeline: list
    ) -> dict:
        """
        SMART skill matching with semantic understanding
        - Uses fuzzy matching for skills (Python matches "Python (Pandas, NumPy)")
        - Infers skills from job roles (Python Developer implies Python skills)
        - No unfair zeros - partial matches get partial credit
        - Completely irrelevant roles still get very low scores
        """
        print("Enhanced LLM Skill Matching (SMART MODE)...")
        
        # Extract candidate's role/title for context
        candidate_roles = [exp.get('role', '') for exp in experience_timeline]
        current_role = resume_data.get('current_role', '')
        
        # Format skills with context
        skills_text = ""
        skills_in_section = []
        skills_in_experience = []
        
        for skill_obj in resume_skills:
            if isinstance(skill_obj, dict):
                if skill_obj['source'] == 'skills_section':
                    skills_in_section.append(skill_obj['skill'])
                else:
                    skills_in_experience.append({
                        "skill": skill_obj['skill'],
                        "context": skill_obj['context']
                    })
        
        system_prompt = """You are a FAIR and INTELLIGENT HR analyst with 20 years of experience.

CRITICAL RULES:
1. SEMANTIC MATCHING: "Python" matches "Python (Pandas, NumPy)" - they're the same core skill
2. FUZZY MATCHING: "SQL" matches "MySQL", "PostgreSQL", "SQL Server" - all SQL databases
3. ROLE-BASED INFERENCE: A "Python Developer" obviously knows Python, even if not explicitly listed
4. PARTIAL CREDIT: Similar skills get 50-70% credit (e.g., "Java" for "JavaScript" = 50%)
5. DEPTH MATTERS: Skills used in projects/jobs worth more than just listed
6. RELEVANCE CHECK: Completely irrelevant roles (Aircraft Engineer for Data Analyst) get 10-20% max
7. NO UNFAIR ZEROS: Everyone with ANY relevant skills gets at least 15-25%

SCORING PHILOSOPHY:
- Perfect match (85-100%): Has the skill, proven in experience
- Good match (60-84%): Has the skill or very similar alternative
- Partial match (35-59%): Has related skills, could learn quickly
- Weak match (15-34%): Has some transferable skills
- No match (0-14%): Completely irrelevant background

Be FAIR, INTELLIGENT, and CONTEXT-AWARE."""
        
        prompt = f"""Analyze candidate skills FAIRLY with SEMANTIC UNDERSTANDING.

CANDIDATE BACKGROUND:
Current/Recent Role: {current_role or (candidate_roles[0] if candidate_roles else 'Unknown')}
All Roles: {', '.join(candidate_roles[:3]) if candidate_roles else 'No experience'}

CANDIDATE SKILLS:

Skills Listed in Resume:
{', '.join(skills_in_section) if skills_in_section else 'None explicitly listed'}

Skills Used in Work Experience:
{json.dumps(skills_in_experience[:20], indent=2) if skills_in_experience else 'None'}

JOB REQUIREMENTS:

MUST-HAVE SKILLS (Primary):
{json.dumps(jd_primary_skills, indent=2)}

GOOD-TO-HAVE SKILLS (Secondary):
{json.dumps(jd_secondary_skills, indent=2)}

HR SKILL WEIGHTAGE (Importance):
{json.dumps(skills_weightage, indent=2)}

SMART MATCHING RULES:

1. FUZZY SKILL MATCHING:
   Examples:
   - JD wants "Python (Pandas, NumPy)" → Candidate has "Python" = MATCH (95%)
   - JD wants "SQL (MySQL / PostgreSQL)" → Candidate has "MySQL" = MATCH (90%)
   - JD wants "Data visualization (Power BI / Tableau)" → Candidate has "Power BI" = MATCH (100%)
   - JD wants "Microsoft Excel (Advanced)" → Candidate has "Excel" = MATCH (85%)
   
2. SEMANTIC EQUIVALENCE:
   - Python = Python3 = Python Programming = 100% match
   - SQL = MySQL = PostgreSQL = SQL Server = 90% match
   - JavaScript = JS = 100% match
   - React = ReactJS = React.js = 100% match
   
3. ROLE-BASED SKILL INFERENCE:
   - "Python Developer" role → Clearly knows Python (even if not listed)
   - "Data Analyst" role → Clearly knows data analysis, SQL, Excel
   - "Backend Developer" role → Clearly knows backend development concepts
   - "DevOps Engineer" role → Clearly knows CI/CD, cloud, automation
   
4. RELATED SKILLS (Partial Credit):
   - Java for JavaScript = 50% (similar syntax, different use)
   - R for Python = 60% (both data science languages)
   - MongoDB for SQL = 40% (both databases, different paradigms)
   - Power BI for Tableau = 85% (both BI tools, very similar)
   
5. EXPERIENCE DEPTH SCORING:
   - Skill only in skills section: 60% of weightage (increased from 40%)
   - Skill used in 1 project/job: 85% of weightage (increased from 70%)
   - Skill used in 2+ projects/jobs: 100% of weightage
   
6. TRANSFERABLE SKILLS:
   - Programming experience → Can learn new languages (add 10-15%)
   - Data analysis experience → Can learn new tools (add 10-15%)
   - Technical background → Faster learning curve (add 5-10%)

7. IRRELEVANCE DETECTION:
   If candidate's background is COMPLETELY DIFFERENT domain:
   - Aircraft Engineer for Software roles = 10-20% max
   - Sales Manager for Data Analyst = 15-25% max
   - Manufacturing Engineer for Backend Developer = 10-20% max
   
   BUT if they have ANY programming/technical skills, give credit!

SCORING CALCULATION:

Step 1: For each JD skill, find best match in candidate's profile
   - Check explicit skills
   - Check skills in experience
   - Infer from job roles/titles
   - Use fuzzy/semantic matching

Step 2: Calculate match score (0-100% per skill)
   - Exact match: 100%
   - Core skill match (Python for "Python (Pandas)"): 90-95%
   - Similar skill: 50-85%
   - Related skill: 30-50%
   - No match: 0%

Step 3: Apply depth multiplier
   - Just listed: 60%
   - Used in 1 job: 85%
   - Used in 2+ jobs: 100%

Step 4: Calculate weighted score
   - Sum: (match_score × depth × skill_weight) for all skills
   - Divide by total weight

Step 5: Apply minimum threshold
   - If ANY relevant skills: minimum 15%
   - If transferable skills: minimum 20%
   - If same domain: minimum 25%
   - If completely different: cap at 20%

Step 6: Add bonuses
   - Secondary skills matched: +5-15%
   - Deep experience in key skills: +5-10%

Return this EXACT JSON format:
{{
  "skill_match_score": <number 0-100>,
  "matched_primary_count": <number of primary skills matched (fuzzy count)>,
  "total_primary_count": <number>,
  "semantic_matches_applied": <number of fuzzy/semantic matches>,
  "role_inferences_applied": <number of skills inferred from roles>,
  "matched_primary_skills": [
    {{
      "skill_required": "Python (Pandas, NumPy)",
      "skill_found": "Python",
      "match_type": "fuzzy|exact|semantic|inferred|related",
      "match_percentage": 95,
      "weightage": 95,
      "depth": "used_in_experience",
      "contexts": ["Backend Developer at XYZ (2 years)"],
      "score_contribution": 90
    }}
  ],
  "missing_primary_skills": [
    {{
      "skill": "AWS",
      "weightage": 60,
      "has_related": false,
      "related_skill": "",
      "gap_severity": "high|medium|low"
    }}
  ],
  "matched_secondary_skills": ["Docker", "Git"],
  "related_skills_bonus": [
    {{
      "required": "MySQL",
      "candidate_has": "PostgreSQL",
      "similarity": "high",
      "partial_credit": 12
    }}
  ],
  "role_based_inferences": [
    {{
      "role": "Python Developer",
      "inferred_skills": ["Python", "Backend Development"],
      "confidence": "high"
    }}
  ],
  "transferable_skills_bonus": 10,
  "domain_relevance": {{
    "candidate_domain": "string",
    "jd_domain": "string",
    "relevance_score": 85,
    "is_same_domain": true
  }},
  "reasoning": "2-3 sentence explanation of fair scoring with semantic matching"
}}

REMEMBER:
- Be INTELLIGENT about matching (Python matches "Python (Pandas)")
- Infer skills from roles (Python Developer knows Python)
- Give partial credit for similar skills
- No unfair zeros unless truly irrelevant
- Check domain relevance (Aircraft Engineer vs Data Analyst)

Return ONLY JSON, no markdown.
"""
        
        try:
            response = self._make_request(prompt, system_prompt, temperature=0.15)
            result = self._parse_json_response(response, "enhanced skill matching")
            
            # Ensure reasonable minimum scores
            score = result.get('skill_match_score', 0)
            matched_count = result.get('matched_primary_count', 0)
            total_count = result.get('total_primary_count', len(jd_primary_skills))
            
            # Apply minimum floor if ANY skills matched
            if matched_count > 0 and score < 15:
                print(f" MINIMUM FLOOR: Raising score from {score} to 15 (has some relevant skills)")
                result['skill_match_score'] = 15
                result['minimum_floor_applied'] = True
            
            # Apply domain relevance check
            domain_relevance = result.get('domain_relevance', {}).get('relevance_score', 100)
            if domain_relevance < 30 and score > 25:
                print(f"DOMAIN CHECK: Capping score to 25 due to low domain relevance ({domain_relevance}%)")
                result['skill_match_score'] = min(score, 25)
                result['domain_cap_applied'] = True
            
            # Ensure score is within bounds
            result['skill_match_score'] = max(0, min(100, result.get('skill_match_score', 0)))
            
            return result
            
        except Exception as e:
            print(f"Enhanced skill matching failed: {e}")
            # Fallback with better minimum
            return {
                "skill_match_score": 20,  # Default to 20% instead of 0
                "matched_primary_count": 0,
                "total_primary_count": len(jd_primary_skills),
                "semantic_matches_applied": 0,
                "role_inferences_applied": 0,
                "matched_primary_skills": [],
                "missing_primary_skills": [{"skill": s, "weightage": skills_weightage.get(s, 50)} for s in jd_primary_skills],
                "matched_secondary_skills": [],
                "related_skills_bonus": [],
                "role_based_inferences": [],
                "transferable_skills_bonus": 0,
                "reasoning": f"LLM analysis failed: {str(e)}, using fallback minimum score"
            }
    
    def enhanced_experience_matching(
        self,
        experience_timeline: list,
        jd_role: str,
        jd_experience_required: str,
        jd_primary_skills: list,
        skills_weightage: dict,
        total_experience_years: float,
        skill_match_score: float = 0
    ) -> dict:
        """
        SMART experience matching with fair role relevance
        - Similar roles get good scores (Backend Dev for Python Dev = 70-80%)
        - Same domain gets decent scores (Data Engineer for Data Analyst = 60-70%)
        - Different domain but technical gets some credit (30-40%)
        - Completely different gets low but not zero (15-25%)
        """
        print("Enhanced LLM Experience Matching (SMART MODE)...")
        
        # Format experience
        exp_summary = []
        for exp in experience_timeline:
            exp_summary.append({
                "role": exp.get('role', 'Unknown'),
                "company": exp.get('company', 'Unknown'),
                "duration": exp.get('duration', 'Unknown'),
                "technologies": exp.get('technologies_used', []),
                "type": self._classify_experience_type(exp)
            })
        
        # Extract experience range from JD
        exp_range = self._parse_experience_range(jd_experience_required)
        
        system_prompt = """You are a FAIR HR analyst who understands career transitions and transferable experience.

CRITICAL RULES:
1. Similar roles in same domain = 70-90% relevance
2. Related roles (Backend Dev → Python Dev) = 60-80% relevance
3. Same domain different role (Data Engineer → Data Analyst) = 55-75% relevance
4. Technical experience for technical role = 40-60% relevance
5. Completely different domain = 15-30% relevance (not 0!)
6. Internships and real projects count
7. Be generous with relevance for career changers with training

NEVER give 0% relevance unless person has NO technical/relevant background at all."""
        
        prompt = f"""Analyze candidate experience FAIRLY with CAREER CONTEXT.

JOB REQUIREMENTS:
- Target Role: {jd_role}
- Experience Required: {jd_experience_required} (Range: {exp_range['min']}-{exp_range['max']} years)
- Key Skills for Role: {', '.join(jd_primary_skills[:5])}

CANDIDATE EXPERIENCE:
- Total Years: {total_experience_years}
- Candidate's Skill Score: {skill_match_score}/100
- Timeline:
{json.dumps(exp_summary, indent=2)}

SMART ROLE MATCHING RULES:

Target Role: "{jd_role}"

ROLE SIMILARITY SCORING (BE FAIR):

1. EXACT MATCH (90-100%):
   - Same title: "Data Analyst" = "Data Analyst"
   - Same title with level: "Data Analyst" = "Senior Data Analyst"
   - Intern version: "Data Analyst Intern" = "Data Analyst" → 85-90%

2. SIMILAR ROLE SAME DOMAIN (70-89%):
   - "Python Developer" for "Backend Developer" → 80%
   - "Backend Developer" for "Python Developer" → 75%
   - "Data Engineer" for "Data Analyst" → 70%
   - "Business Intelligence Analyst" for "Data Analyst" → 75%
   - "DevOps Engineer" for "Backend Developer" → 65%

3. RELATED ROLE SIMILAR DOMAIN (50-69%):
   - "Full Stack Developer" for "Backend Developer" → 65%
   - "Software Engineer" for "Python Developer" → 60%
   - "Business Analyst" for "Data Analyst" → 50%
   - "QA Engineer" for "Backend Developer" → 45%

4. TECHNICAL BUT DIFFERENT FOCUS (30-49%):
   - "Frontend Developer" for "Backend Developer" → 40%
   - "Mobile Developer" for "Web Developer" → 35%
   - "Data Scientist" for "Backend Developer" → 30%

5. DIFFERENT DOMAIN BUT TECHNICAL (15-29%):
   - "Mechanical Engineer" (if has programming) for "Software Engineer" → 25%
   - "Network Engineer" for "Backend Developer" → 25%
   - "Manufacturing Engineer" (if has data analysis) for "Data Analyst" → 20%

6. COMPLETELY DIFFERENT (5-14%):
   - "Sales Manager" for "Data Analyst" → 10%
   - "HR Executive" for "Backend Developer" → 8%
   - "Aircraft Engineer" (no tech skills) for "Software Role" → 5%

IMPORTANT: If skill_match_score > 40%, give benefit of doubt - they clearly have relevant skills!

EXPERIENCE CEILING RULES (FAIR):

For JD requiring "{jd_experience_required}":

IF JD = 0-2 years:
- 0 years (Fresher with relevant skills): MAX 60
- 0 years (Fresher with NO skills): MAX 30
- 0.5-1 year (Intern/Entry): MAX 75
- 1-2 years (Ideal): MAX 95
- 2-3 years: MAX 90
- 3-4 years: MAX 80
- 5+ years: MAX 70

IF JD = 2-5 years:
- 0-1 years: MAX 50
- 1-2 years: MAX 70
- 2-4 years (Ideal): MAX 95
- 4-6 years: MAX 90
- 7+ years: MAX 75

IF JD = 5+ years:
- 0-2 years: MAX 30
- 2-4 years: MAX 60
- 4-6 years: MAX 80
- 5-8 years (Ideal): MAX 95
- 9+ years: MAX 100

SCORING CALCULATION:

Step 1: Calculate role relevance (use fair rules above)
Step 2: If skill_match_score > 40 → boost role relevance by 10-15%
Step 3: Calculate base score = role_relevance × (100 - overqualification_penalty)
Step 4: Add recency bonus (max +15)
Step 5: Add internship/project bonus if applicable (+10)
Step 6: Determine ceiling based on years
Step 7: Apply: final_score = min(base_score + bonuses, ceiling)

FRESHER PROTECTION:
If total_experience == 0 BUT skill_match_score > 40:
→ Don't penalize too much, they have the skills!
→ Use skill_match_score as reference, allow 60-70% of it

Return this EXACT JSON format:
{{
  "experience_match_score": <number 0-100>,
  "calculated_base_score": <number before ceiling>,
  "applied_ceiling": <number>,
  "ceiling_reason": "string explanation",
  "relevant_experience_years": <number>,
  "has_matching_role_experience": <true/false>,
  "experience_type": "fresher|intern|junior|experienced|senior",
  "role_relevance_percentage": <0-100>,
  "matching_roles": [
    {{
      "role": "Backend Developer",
      "company": "XYZ Corp",
      "duration": "2021-2023",
      "years": 2.0,
      "relevance": "exact|similar|related|different",
      "relevance_score": 80,
      "is_recent": true,
      "is_internship": false,
      "technologies_used": ["Python", "Django"]
    }}
  ],
  "non_matching_roles": [],
  "experience_level_assessment": {{
    "required_range": "{exp_range['min']}-{exp_range['max']} years",
    "candidate_has": <number>,
    "status": "perfect_match|within_range|slightly_below|overqualified|underqualified"
  }},
  "recency_bonus": <number 0-20>,
  "skill_based_boost": <number 0-15>,
  "overqualification_flag": {{
    "is_overqualified": <true/false>,
    "severity": "none|mild|moderate",
    "penalty_applied": <number>
  }},
  "fresher_protection_applied": <true/false>,
  "career_progression_notes": ["note1"],
  "reasoning": "Fair explanation of scoring with career context"
}}

CRITICAL REMINDERS:
1. Be FAIR with role matching - similar roles get good scores
2. Consider skill_match_score - if high, be generous with experience
3. Don't penalize career changers with relevant skills
4. Internships and projects count
5. Technical background for technical role = reasonable relevance

Return ONLY JSON, no markdown.
"""
        
        try:
            response = self._make_request(prompt, system_prompt, temperature=0.15)
            result = self._parse_json_response(response, "enhanced experience matching")
            
            # Ensure reasonable scoring
            exp_score = result.get('experience_match_score', 0)
            role_relevance = result.get('role_relevance_percentage', 0)
            
            # If skill score is high but experience score is too low, adjust
            if skill_match_score > 40 and exp_score < 30 and role_relevance < 40:
                print(f" SKILL-BASED BOOST: Raising experience score due to high skill match")
                result['experience_match_score'] = min(exp_score + 15, 50)
                result['skill_based_boost_applied'] = True
            
            # Ensure score is within bounds
            if 'experience_match_score' in result:
                result['experience_match_score'] = max(0, min(100, result['experience_match_score']))
            
            return result
            
        except Exception as e:
            print(f"Enhanced experience matching failed: {e}")
            return {
                "experience_match_score": 30,  # Default to 30% instead of 0
                "calculated_base_score": 30,
                "applied_ceiling": 100,
                "ceiling_reason": "Fallback scoring",
                "relevant_experience_years": total_experience_years,
                "has_matching_role_experience": False,
                "experience_type": "unknown",
                "role_relevance_percentage": 30,
                "matching_roles": [],
                "non_matching_roles": experience_timeline,
                "reasoning": f"LLM analysis failed: {str(e)}, using fallback minimum"
            }
    
    def _classify_experience_type(self, exp: dict) -> str:
        """Classify if experience is internship, full-time, etc."""
        role = exp.get('role', '').lower()
        company = exp.get('company', '').lower()
        duration = exp.get('duration', '').lower()
        
        if 'intern' in role or 'intern' in company or 'internship' in duration:
            return "internship"
        elif 'contract' in role or 'freelance' in role:
            return "contract"
        elif 'part-time' in duration or 'part time' in duration:
            return "part-time"
        else:
            return "full-time"
    
    def calculate_final_ats_score_v2(
        self,
        skill_analysis: dict,
        experience_analysis: dict,
        candidate_name: str,
        jd_title: str,
        jd_experience_required: str,
        total_experience_years: float
    ) -> dict:
        """
        FAIR final score calculation
        - No automatic rejection unless truly no relevance
        - Balances skills and experience intelligently
        """
        print("Enhanced Final Score Calculation (FAIR MODE)...")
        
        skill_score = skill_analysis.get('skill_match_score', 0)
        exp_score = experience_analysis.get('experience_match_score', 0)
        
        system_prompt = """You are a FAIR ATS system that gives everyone a chance while being honest about fit.

Never give 0% overall score unless absolutely no relevance."""
        
        prompt = f"""Calculate final ATS score FAIRLY.

CANDIDATE: {candidate_name}
JOB: {jd_title}
EXPERIENCE REQUIRED: {jd_experience_required}
CANDIDATE EXPERIENCE: {total_experience_years} years

SKILL ANALYSIS:
{json.dumps(skill_analysis, indent=2)}

EXPERIENCE ANALYSIS:
{json.dumps(experience_analysis, indent=2)}

FORMULA:
Final Score = (Skill Score × 50%) + (Experience Score × 50%)

Skill Score = {skill_score}, Experience Score = {exp_score}

DECISION LOGIC:
- 75-100: Strong Fit - Highly Recommended
- 55-74: Good Fit - Recommended  
- 35-54: Moderate Fit - Consider with interview
- 20-34: Weak Fit - Long shot but possible
- 0-19: Poor Fit - Not recommended

Return EXACT JSON:
{{
  "overall_score": <number 0-100>,
  "skill_component": {skill_score},
  "experience_component": {exp_score},
  "recommendation": "strong_fit|good_fit|moderate_fit|weak_fit|poor_fit",
  "hiring_decision": "highly_recommended|recommended|consider|interview_to_decide|not_recommended",
  "score_explanation": [
    "Line 1",
    "Line 2"
  ],
  "key_strengths": ["strength1"],
  "key_concerns": ["concern1"],
  "interview_recommendation": "string"
}}

Be honest but fair. Return ONLY JSON.
"""
        
        try:
            response = self._make_request(prompt, system_prompt, temperature=0.2)
            result = self._parse_json_response(response, "final score calculation v2")
            
            # Calculate overall score
            overall = (skill_score * 0.5) + (exp_score * 0.5)
            
            if 'overall_score' not in result:
                result['overall_score'] = overall
            
            result['overall_score'] = max(0, min(100, result['overall_score']))
            result['skill_component'] = skill_score
            result['experience_component'] = exp_score
            
            return result
            
        except Exception as e:
            print(f"Final scoring failed: {e}")
            overall = (skill_score + exp_score) / 2
            
            return {
                "overall_score": overall,
                "skill_component": skill_score,
                "experience_component": exp_score,
                "recommendation": "moderate_fit" if overall > 40 else "weak_fit",
                "hiring_decision": "consider" if overall > 40 else "interview_to_decide",
                "score_explanation": [
                    f"Skill Score: {skill_score:.1f}/100 (50% weight)",
                    f"Experience Score: {exp_score:.1f}/100 (50% weight)"
                ],
                "key_strengths": ["Has some relevant background"],
                "key_concerns": ["LLM analysis unavailable"]
            }
    
    def _parse_experience_range(self, exp_str: str) -> dict:
        """Parse experience range from string like '0-2 years' or '5+ years'"""
        exp_str = exp_str.lower().strip()
        
        # Handle "X+ years"
        if '+' in exp_str:
            match = re.search(r'(\d+)\+', exp_str)
            if match:
                min_years = int(match.group(1))
                return {"min": min_years, "max": 100}
        
        # Handle "X-Y years"
        match = re.search(r'(\d+)\s*-\s*(\d+)', exp_str)
        if match:
            return {"min": int(match.group(1)), "max": int(match.group(2))}
        
        # Handle single number
        match = re.search(r'(\d+)', exp_str)
        if match:
            years = int(match.group(1))
            return {"min": years, "max": years + 2}
        
        # Default
        return {"min": 0, "max": 2}
    
    # Keep all other existing methods (structure_job_description, extract_resume_information, etc.)

    def structure_job_description(self, jd_text: str) -> Dict[str, Any]:
        """Extract structured data from job description"""
        print("Structuring Job Description with llama.cpp...")
        
        system_prompt = """You are an expert HR assistant specializing in analyzing job descriptions. 
Extract information and return ONLY valid JSON with no extra text."""
        
        prompt = f"""Analyze this job description and extract information into JSON format.

Required JSON structure:
{{
    "job_title": "string",
    "company": "string or 'Not specified'",
    "location": "string or 'Not specified'",
    "experience_required": "string (e.g., '0-2 years' or '3-5 years')",
    "primary_skills": ["skill1", "skill2", ...],
    "secondary_skills": ["skill1", "skill2", ...],
    "responsibilities": ["resp1", "resp2", ...],
    "qualifications": ["qual1", "qual2", ...],
    "job_type": "Full-time|Part-time|Contract|etc"
}}

Job Description:
{jd_text[:2000]}

Return ONLY the JSON object, no explanations.
"""
        
        response = self._make_request(prompt, system_prompt, temperature=0.1)
        return self._parse_json_response(response, "job description")
    
    def extract_resume_information(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured data from resume"""
        print("Extracting Resume Information with llama.cpp...")
        
        system_prompt = """You are an expert resume parser. Extract information accurately and return ONLY valid JSON."""
        
        prompt = f"""Extract resume information and return as JSON.

Required JSON structure:
{{
    "name": "Full name",
    "email": "email@example.com",
    "phone": "phone number",
    "linkedin": "LinkedIn URL or 'Not provided'",
    "github": "GitHub URL or 'Not provided'",
    "portfolio": "Portfolio URL or 'Not provided'",
    "current_role": "Current job title",
    "total_experience": 0,
    "skills": ["skill1", "skill2", "skill3"],
    "education": ["degree1", "degree2"],
    "certifications": ["cert1", "cert2"],
    "experience_timeline": [
        {{
            "company": "Company name",
            "role": "Job title",
            "duration": "Time period",
            "technologies_used": ["tech1", "tech2"]
        }}
    ]
}}

IMPORTANT:
- skills MUST be an array of strings
- Extract ALL technical skills
- total_experience must be a number (years) - if fresher/no experience, use 0
- If no experience, experience_timeline should be []

Resume Text:
{resume_text[:2000]}

Return ONLY valid JSON.
"""
        
        response = self._make_request(prompt, system_prompt, temperature=0.1)
        parsed = self._parse_json_response(response, "resume")
        
        # Ensure skills is an array
        if 'skills' in parsed:
            if isinstance(parsed['skills'], dict):
                parsed['skills'] = list(parsed['skills'].values())
            elif isinstance(parsed['skills'], str):
                parsed['skills'] = [s.strip() for s in parsed['skills'].split(',') if s.strip()]
            elif not isinstance(parsed['skills'], list):
                parsed['skills'] = []
        else:
            parsed['skills'] = []
        
        # Ensure total_experience is a number
        if 'total_experience' not in parsed or parsed['total_experience'] is None:
            parsed['total_experience'] = 0
        
        return parsed
    
    def generate_interview_questions(self, jd_data: dict, difficulty_level: str = "medium-hard") -> list:
        """Generate interview questions based on job description"""
        print(f"Generating interview questions...")
        
        job_title = jd_data.get('job_title', 'Software Engineer')
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        experience_required = jd_data.get('experience_required', '2-3 years')
        responsibilities = jd_data.get('responsibilities', [])
        
        all_skills = primary_skills + secondary_skills
        skills_text = ', '.join(all_skills) if all_skills else 'general technical skills'
        
        system_prompt = """You are an expert technical interviewer. Generate high-quality, practical questions. Return ONLY a valid JSON array."""
        
        prompt = f"""Generate exactly 10 interview questions for a {job_title} position.

CONTEXT:
- Experience Required: {experience_required}
- Key Skills: {skills_text}
- Difficulty: {difficulty_level}

REQUIREMENTS:
1. Mix: 40% technical, 30% problem-solving, 20% system design, 10% behavioral
2. Practical, not theoretical
3. Specific to {job_title} and {skills_text}

RESPONSIBILITIES:
{chr(10).join(responsibilities[:5]) if responsibilities else 'Standard tasks'}

Return format:
[
  "Question 1",
  "Question 2",
  ...
  "Question 10"
]

Return ONLY the JSON array.
"""
        
        try:
            response = self._make_request(prompt, system_prompt, temperature=0.3)
            
            # Try parsing
            try:
                questions = json.loads(response)
                if isinstance(questions, list) and len(questions) >= 10:
                    return questions[:10]
            except:
                pass
            
            # Extract from markdown
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group(1))
                if isinstance(questions, list) and len(questions) >= 10:
                    return questions[:10]
            
            # Fallback: line by line
            lines = [l.strip() for l in response.split('\n') if l.strip() and len(l) > 20]
            questions = [re.sub(r'^\d+[\.\)]\s*', '', l).strip('"').strip("'") for l in lines]
            
            if len(questions) >= 10:
                return questions[:10]
            
            raise Exception("Could not extract 10 questions")
        
        except Exception as e:
            print(f"Error generating questions: {e}")
            raise
    
    def detect_job_roles_and_priorities(self, jd_data: dict) -> list:
        """Detect job roles and priorities using LLM"""
        job_title = jd_data.get('job_title', 'Unknown')
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        
        system_prompt = """You are an expert HR analyst. Identify relevant job roles. Return ONLY valid JSON array."""
        
        prompt = f"""Identify TOP 3 most relevant job roles for this JD in priority order.

JOB TITLE: {job_title}
PRIMARY SKILLS: {', '.join(primary_skills)}
SECONDARY SKILLS: {', '.join(secondary_skills)}

Return EXACT format:
[
  {{
    "role": "Specific role name",
    "priority": 1,
    "key_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
    "weight": 1.0
  }},
  {{
    "role": "Second role",
    "priority": 2,
    "key_skills": ["skill1", "skill2", "skill3", "skill4"],
    "weight": 0.8
  }},
  {{
    "role": "Third role",
    "priority": 3,
    "key_skills": ["skill1", "skill2", "skill3"],
    "weight": 0.6
  }}
]

Rules:
- Be SPECIFIC (include tech/domain in role name)
- Priority 1 is MOST important
- key_skills must match JD skills

Return ONLY JSON.
"""
        
        try:
            response = self._make_request(prompt, system_prompt, temperature=0.2)
            
            # Try direct parse
            try:
                roles = json.loads(response.strip())
                if self._validate_roles(roles):
                    return roles[:3]
            except:
                pass
            
            # Extract from markdown
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
            if json_match:
                roles = json.loads(json_match.group(1))
                if self._validate_roles(roles):
                    return roles[:3]
            
            raise Exception("Could not parse role detection")
        
        except Exception as e:
            print(f"Role detection error: {e}")
            raise
    
    def _validate_roles(self, roles) -> bool:
        """Validate role detection output"""
        if not isinstance(roles, list) or len(roles) == 0:
            return False
        
        for role in roles:
            if not isinstance(role, dict):
                return False
            if 'role' not in role or 'priority' not in role or 'key_skills' not in role:
                return False
            if not isinstance(role['key_skills'], list) or len(role['key_skills']) == 0:
                return False
        
        return True
    
    def _parse_json_response(self, response: str, operation: str) -> Dict[str, Any]:
        """Extract and parse JSON from llama.cpp response"""
        try:
            # Try direct parsing
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Extract from markdown
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Look for JSON anywhere
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            print(f"Could not extract JSON from {operation}")
            print(f"Response preview: {response[:200]}")
            
            return {"error": f"Failed to parse {operation}", "raw_response": response[:500]}
        
        except Exception as e:
            print(f"Parse error in {operation}: {str(e)}")
            return {"error": f"Failed to parse {operation}", "exception": str(e)}
    
    def health_check(self) -> bool:
        """Check if llama.cpp server is accessible"""
        try:
            response = self._make_request("Hello, are you working?", temperature=0.1)
            return bool(response and len(response) > 0)
        except Exception as e:
            print(f"llama.cpp health check failed: {str(e)}")
            return False


# Singleton instance
_llamacpp_service = None

def get_llamacpp_service() -> LlamaCppService:
    """Get or create LlamaCppService singleton"""
    global _llamacpp_service
    if _llamacpp_service is None:
        _llamacpp_service = LlamaCppService()
    return _llamacpp_service