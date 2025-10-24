import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from backend.app.config import settings
import json
import re
import asyncio

load_dotenv()

class EnhancedAgenticATSService:
    def __init__(self):
        # Determine which LLM backend to use
        self.use_groq = os.getenv("USE_GROQ", "true").lower() == "true"
        use_perplexity = os.getenv("USE_PERPLEXITY", "true").lower() == "true"

        if use_perplexity:
            self.llm = LLM(
                model=f"perplexity/{settings.PERPLEXITY_MODEL}",  
                api_key=os.getenv("PERPLEXITY_API_KEY"),
                base_url="https://api.perplexity.ai",
                temperature=0.1
            )
            print(f"✅ Using Perplexity: {settings.PERPLEXITY_MODEL}")

        elif self.use_groq:
            self.llm = LLM(
                model=f"groq/{settings.GROQ_MODEL}", 
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.1
            )
            print(f"✅ Using Groq: {settings.GROQ_MODEL}")

        else:
            self.llm = LLM(
                model=f"{settings.OPENAI_MODEL}",  
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.1
            )
            print(f"✅ Using OpenAI: {settings.OPENAI_MODEL}")


        # Initialize specialized agents
        self.resume_analyzer = self._create_resume_analyzer()
        self.jd_analyzer = self._create_jd_analyzer()
        self.skills_matcher = self._create_skills_matcher()
        self.experience_evaluator = self._create_experience_evaluator()
        self.scorer = self._create_scorer()

    
    def _create_resume_analyzer(self) -> Agent:
        return Agent(
            role="Senior Resume Analysis Expert",
            goal="Extract and structure ALL relevant information from candidate resumes with perfect accuracy",
            backstory="""You are an expert HR professional with 15 years of experience in
            resume screening. You excel at extracting structured data from unstructured text.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )
    
    def _create_jd_analyzer(self) -> Agent:
        return Agent(
            role="Senior Job Description Analysis Expert",
            goal="Extract and prioritize requirements from job descriptions",
            backstory="""You are a senior technical recruiter with 12 years of experience
            who understands what companies truly need.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )
    
    def _create_skills_matcher(self) -> Agent:
        return Agent(
            role="Technical Skills Matching Specialist",
            goal="Accurately match candidate skills with job requirements",
            backstory="""You are a technical assessment expert who deeply understands
            technology stacks and can identify skill overlaps.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )
    
    def _create_experience_evaluator(self) -> Agent:
        return Agent(
            role="Experience Evaluation Specialist",
            goal="Evaluate candidate experience depth, relevance, and progression",
            backstory="""You are a seasoned technical hiring manager who evaluates
            quality and relevance of experience.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )
    
    def _create_scorer(self) -> Agent:
        return Agent(
            role="Candidate Scoring & Ranking Expert",
            goal="Provide fair, accurate, and defensible candidate scores",
            backstory="""You are an experienced hiring manager who makes data-driven
            hiring decisions.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )
    
    async def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """Analyze resume using Resume Analyzer agent"""
        print("Analyzing resume with Agentic AI...")
    
        task = Task(
            description=f"""
            Extract resume information from the following text and return ONLY a valid JSON object.
        
            **CRITICAL: Skills MUST be an array of strings, not objects or dictionaries.**
        
            Required JSON structure:
            {{
                "name": "Full name",
                "email": "email@example.com",
                "phone": "phone number",
                "linkedin": "LinkedIn URL",
                "github": "GitHub URL",
                "portfolio": "Portfolio URL",
                "current_role": "Current job title",
                "total_experience": 0,
                "skills": ["skill1", "skill2", "skill3"],  <-- MUST BE ARRAY OF STRINGS
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
        
            **IMPORTANT RULES:**
            1. skills MUST be a flat array of strings: ["Python", "Java", "SQL"]
            2. Do NOT use objects or nested structures for skills
            3. Extract ALL technical skills mentioned (programming languages, frameworks, tools, databases)
            4. Normalize skill names (e.g., "python" → "Python", "react.js" → "React")
            5. total_experience must be a number (years)
        
            Resume Text:
            {resume_text[:2000]}
        
            Return ONLY valid JSON, no explanations, no markdown.
            """,
            agent=self.resume_analyzer,
            expected_output="Valid JSON with resume data"
        )
    
        crew = Crew(
            agents=[self.resume_analyzer],
            tasks=[task],
            verbose=False,
            process=Process.sequential
        )
    
        result = crew.kickoff()
        parsed_result = self._parse_json_result(result, "resume analysis")
    
        # POST-PROCESSING: Ensure skills is always an array
        if 'skills' in parsed_result:
            if isinstance(parsed_result['skills'], dict):
                parsed_result['skills'] = list(parsed_result['skills'].values())
            elif isinstance(parsed_result['skills'], str):
                parsed_result['skills'] = [s.strip() for s in parsed_result['skills'].split(',') if s.strip()]
            elif not isinstance(parsed_result['skills'], list):
                parsed_result['skills'] = []
        else:
            parsed_result['skills'] = []
    
        # Ensure total_experience is a number
        if 'total_experience' in parsed_result:
            try:
                parsed_result['total_experience'] = float(parsed_result['total_experience'])
            except:
                parsed_result['total_experience'] = 0
        else:
            parsed_result['total_experience'] = 0
    
        print(f"Extracted {len(parsed_result.get('skills', []))} skills from resume")
    
        return parsed_result

    
    async def analyze_job_description(self, jd_text: str) -> Dict[str, Any]:
        """Analyze JD using JD Analyzer agent"""
        print("Analyzing job description with Agentic AI...")
    
        task = Task(
            description=f"""Analyze this job description and extract ONLY a JSON object with these exact fields:
            - job_title (string)
            - company (string)
            - location (string)
            - experience_required (string)
            - primary_skills (array of strings)
            - secondary_skills (array of strings)
            - responsibilities (array of strings)
            - qualifications (array of strings)
            - job_type (string)
        
            Job Description:
            {jd_text[:1000]}
        
            Return ONLY the JSON object, nothing else. No explanations, no markdown.""",
            agent=self.jd_analyzer,
            expected_output="Valid JSON object with job description fields"
        )
    
        crew = Crew(
            agents=[self.jd_analyzer],
            tasks=[task],
            verbose=True, 
            process=Process.sequential
        )
    
        result = crew.kickoff()
        return self._parse_json_result(result, "job description analysis")
    
    async def match_and_score(self, jd_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        NEW METHOD: Comprehensive matching and scoring using Agentic AI
        This method was missing and causing the AttributeError
        """
        print("Starting Agentic AI matching and scoring...")
        
        # Create comprehensive matching task
        matching_task = Task(
            description=f"""
            You are an expert ATS system. Analyze this candidate against the job requirements.
            
            **Job Requirements:**
            - Position: {jd_data.get('job_title', 'Unknown')}
            - Required Experience: {jd_data.get('experience_required', 'Not specified')}
            - Primary Skills: {', '.join(jd_data.get('primary_skills', []))}
            - Secondary Skills: {', '.join(jd_data.get('secondary_skills', []))}
            
            **Candidate Profile:**
            - Name: {resume_data.get('name', 'Unknown')}
            - Experience: {resume_data.get('total_experience', 0)} years
            - Skills: {', '.join(resume_data.get('skills', []))}
            
            Provide a comprehensive ATS score breakdown as JSON:
            {{
                "overall_score": <number 0-100>,
                "skill_match_score": <number 0-100>,
                "experience_score": <number 0-100>,
                "matched_skills": [<array of matched skills>],
                "missing_skills": [<array of missing critical skills>],
                "experience_gap": "<description of experience gap>",
                "strengths": [<array of key strengths>],
                "concerns": [<array of concerns>],
                "recommendation": "<STRONG_FIT|MODERATE_FIT|WEAK_FIT>"
            }}
            
            Return ONLY valid JSON, no explanations.
            """,
            agent=self.scorer,
            expected_output="Valid JSON with comprehensive scoring"
        )
        
        crew = Crew(
            agents=[self.scorer],
            tasks=[matching_task],
            verbose=False,
            process=Process.sequential
        )
        
        try:
            result = crew.kickoff()
            scoring_data = self._parse_json_result(result, "matching and scoring")
            
            # Ensure required fields exist
            return {
                "overall_score": scoring_data.get("overall_score", 0),
                "skill_match_score": scoring_data.get("skill_match_score", 0),
                "experience_score": scoring_data.get("experience_score", 0),
                "matched_skills": scoring_data.get("matched_skills", []),
                "missing_skills": scoring_data.get("missing_skills", []),
                "experience_gap": scoring_data.get("experience_gap", ""),
                "strengths": scoring_data.get("strengths", []),
                "concerns": scoring_data.get("concerns", []),
                "recommendation": scoring_data.get("recommendation", "MODERATE_FIT")
            }
        except Exception as e:
            print(f"❌ Agentic scoring failed: {e}")
            # Return fallback scores
            return {
                "overall_score": 0,
                "skill_match_score": 0,
                "experience_score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "experience_gap": "Unable to evaluate",
                "strengths": [],
                "concerns": ["Scoring failed"],
                "recommendation": "WEAK_FIT"
            }
    
    def _parse_json_result(self, result: Any, operation: str) -> Dict[str, Any]:
        """Parse JSON from crew result which handles various LLM response formats"""
        try:
            result_str = str(result)
        
            # Try direct JSON parse first
            try:
                return json.loads(result_str)
            except json.JSONDecodeError:
                pass
        
            # Extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        
            # Look for JSON object anywhere in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        
            print(f"⚠️ Could not extract JSON from: {result_str[:500]}")
            return {"error": f"Failed to parse {operation}", "raw_response": result_str[:200]}
        
        except Exception as e:
            print(f"❌ Parse error in {operation}: {str(e)}")
            return {"error": f"Failed to parse {operation}", "exception": str(e)}
    
    async def refine_job_description_structure(self, current_structure: Dict, feedback: str) -> Dict[str, Any]: 
        """Refine JD structure based on user feedback"""
        print(f"🤖 Refining JD structure with Agentic AI based on feedback...")
        print(f"📝 Feedback: {feedback}")
    
        refinement_agent = Agent(
            role="Job Description Refinement Specialist",
            goal="Precisely refine job descriptions based on user feedback while maintaining structure integrity",
            backstory="""You are an expert HR tech specialist with deep understanding of 
            job descriptions and ATS systems. You excel at understanding user feedback and 
            applying precise modifications to job descriptions.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
        refinement_task = Task(
            description=f"""
            **CRITICAL INSTRUCTIONS:**
        
            You MUST refine this job description structure based on user feedback.
        
            **Current Job Description Structure:**
            ```
            {json.dumps(current_structure, indent=2)}
            ```
        
            **User Feedback:**
            "{feedback}"
        
            **Your Task:**
            1. Carefully analyze the feedback to understand what changes are requested
            2. Identify specific modifications (add skills, change experience, etc.)
            3. Apply the changes precisely while preserving all other fields
            4. Maintain the exact JSON structure with all required fields
            5. Do NOT remove or modify existing content unless explicitly requested
        
            **IMPORTANT:** Return ONLY valid JSON. No explanations, no markdown, no code blocks.
            
            **Example:**
            - Feedback: "add Python to primary skills"
            - Action: Add "Python" to primary_skills array
            """,
            agent=refinement_agent,
            expected_output="Valid JSON object with refined job description structure"
        )
    
        crew = Crew(
            agents=[refinement_agent],
            tasks=[refinement_task],
            verbose=True
        )
    
        try:
            print("🚀 Executing refinement crew...")
            result = crew.kickoff()
            result_str = str(result)
        
            # Try to parse as JSON directly
            try:
                refined_data = json.loads(result_str)
                print("✅ Successfully parsed JSON directly")
                return refined_data
            except json.JSONDecodeError:
                print("⚠️ Direct JSON parsing failed, trying regex extraction...")
            
                json_patterns = [
                    r'```json\s*(\{[\s\S]*?\})\s*```',
                    r'```\s*(\{[\s\S]*?\})\s*```',
                    r'(\{[\s\S]*\})', 
                ]
            
                for pattern in json_patterns:
                    match = re.search(pattern, result_str, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1).strip()
                            refined_data = json.loads(json_str)
                            print(f"✅ Successfully extracted JSON using pattern")
                            return refined_data
                        except json.JSONDecodeError:
                            continue
            
                raise Exception("Failed to parse refined structure from AI response")
    
        except Exception as e:
            print(f"❌ Agentic AI refinement error: {str(e)}")
            raise Exception(f"Agentic refinement failed: {str(e)}")