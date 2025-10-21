import json
import os
from typing import Dict, Any, List
from .llm_service import LLMService

class InterviewService:
    def __init__(self):
        self.llm_service = LLMService()
    
    async def generate_interview_questions(self, jd_data: Dict[str, Any], difficulty_level: str = "medium-hard") -> List[str]:
        #Generaing interview questions based on JD skills and requirements
        
        # Extracting skills from JD
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        job_title = jd_data.get('job_title', 'Software Engineer')
        experience_required = jd_data.get('experience_required', '2-3 years')
        responsibilities = jd_data.get('responsibilities', [])
        
        # Combining all skills
        all_skills = primary_skills + secondary_skills
        skills_text = ', '.join(all_skills) if all_skills else 'general technical skills'
        
        # Creating comprehensive prompt
        prompt = f"""
Generate exactly 10 interview questions for a {job_title} position requiring {experience_required} of experience.

REQUIREMENTS:
- Questions should be {difficulty_level} level (challenging but fair)
- Focus on these key skills: {skills_text}
- Mix of technical, behavioral, and problem-solving questions
- Questions should test practical knowledge, not just theory
- Include scenario-based questions related to the role
- No basic/easy questions - candidates should have real experience

JOB RESPONSIBILITIES:
{chr(10).join(responsibilities) if responsibilities else 'Standard software development responsibilities'}

FORMAT: Return ONLY a JSON array of exactly 10 questions as strings:
["Question 1", "Question 2", "Question 3", ...]

QUESTION TYPES TO INCLUDE:
- Technical deep-dive questions (40%)
- Problem-solving scenarios (30%) 
- System design/architecture (20%)
- Behavioral/experience-based (10%)

Make questions specific to {job_title} role and {skills_text} skills.
"""

        try:
            print(f"Generating interview questions for {job_title}...")
            response = await self.llm_service._make_api_call(prompt)
            
            # Trying to parse JSON response
            try:
                questions = json.loads(response)
                if isinstance(questions, list) and len(questions) >= 10:
                    return questions[:10]  # Return exactly 10 questions
                else:
                    raise ValueError("Invalid response format")
            except (json.JSONDecodeError, ValueError):
                # Trying to extract JSON from response
                import re
                json_match = re.search(r'\[(.*?)\]', response, re.DOTALL)
                if json_match:
                    questions = json.loads(json_match.group())
                    return questions[:10] if len(questions) >= 10 else questions
                else:
                    # Fallback split by lines and clean up
                    lines = response.split('\n')
                    questions = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and len(line) > 20:
                            # Clean up common prefixes
                            line = re.sub(r'^\d+[\.\)]\s*', '', line)
                            line = line.strip('"').strip("'").strip()
                            if line:
                                questions.append(line)
                    
                    return questions[:10] if len(questions) >= 10 else questions
                    
        except Exception as e:
            print(f"Error generating interview questions: {str(e)}")
            # Returning fallback questions based on skills
            return self._generate_fallback_questions(all_skills, job_title)
    
    def _generate_fallback_questions(self, skills: List[str], job_title: str) -> List[str]:
        #Generate fallback questions when API fails
        base_questions = [
            f"Describe a challenging project you've worked on as a {job_title} and how you overcame technical obstacles.",
            f"How would you design a scalable system for a high-traffic application in your domain?",
            f"Walk me through your approach to debugging a critical production issue.",
            f"Explain a time when you had to learn a new technology quickly for a project.",
            f"How do you ensure code quality and maintainability in your development process?",
            f"Describe your experience with collaborative development and code reviews.",
            f"What strategies do you use for optimizing application performance?",
            f"How would you handle conflicting requirements from different stakeholders?",
            f"Explain your approach to testing and quality assurance.",
            f"Describe a situation where you had to refactor legacy code."
        ]
        
        # Customizing based on skills if available
        if skills:
            skill_specific = []
            for skill in skills[:3]:
                skill_specific.append(f"How would you implement a complex feature using {skill}? Walk me through your approach.")
            base_questions[:len(skill_specific)] = skill_specific
        
        return base_questions